import os
import re
import socket
import subprocess
import requests
import ipaddress
import dns.resolver
from django.utils import timezone
from control.models import user

SERVER_IPS = {'207.180.209.216', '127.0.0.1'}

CLOUDFLARE_PREFIXES = (
    '173.245.', '103.21.', '103.22.', '103.31.', '141.101.',
    '108.162.', '190.93.', '188.114.', '197.234.', '198.41.',
    '162.158.', '162.159.', '104.16.', '104.17.', '104.18.',
    '104.19.', '104.20.', '104.21.', '104.22.', '104.23.',
    '104.24.', '104.25.', '104.26.', '104.27.', '172.64.',
    '172.65.', '172.66.', '172.67.', '172.68.', '172.69.',
    '172.70.', '172.71.', '131.0.72.'
)

DUMMY_DOMAINS = {
    'example.com', 'example.org', 'example.net', 'test.com',
    'localhost', 'local', 'invalid', 'voidpanel.local',
    'mailinator.com', 'tempmail.com', '10minutemail.com',
    'guerrillamail.com', 'sharklasers.com', 'fake.com'
}

DUMMY_LOCALPARTS = {
    'test', 'testing', 'fake', 'none', 'dummy', 'asdf', 'sample', 'null'
}

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

def resolve_q(resolver, qname, rdtype):
    if hasattr(resolver, 'resolve'):
        return resolver.resolve(qname, rdtype)
    return resolver.query(qname, rdtype)

def is_bogon_or_private(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_unspecified
    except ValueError:
        return True

def clean_domain_name(raw_domain):
    if not raw_domain:
        return ''
    d = raw_domain.strip().lower()
    d = re.sub(r'^https?://', '', d)
    d = d.split('/')[0].split(':')[0]
    return d

def is_cloudflare_ip(ip):
    if not ip:
        return False
    return any(ip.startswith(prefix) for prefix in CLOUDFLARE_PREFIXES)

def check_domain_status(clean_domain):
    """
    Returns (is_active: bool, ip: str, message: str)
    """
    if not clean_domain or '.' not in clean_domain:
        return False, '', 'Invalid domain format'
    
    # 1. Resolve DNS
    resolved_ip = None
    try:
        resolved_ip = socket.gethostbyname(clean_domain)
    except Exception:
        # Fallback to host command
        try:
            res = subprocess.run(['host', '-t', 'A', clean_domain], capture_output=True, text=True, timeout=2)
            for line in res.stdout.splitlines():
                if 'has address' in line:
                    resolved_ip = line.split('has address')[-1].strip()
                    break
        except Exception:
            pass

    if not resolved_ip:
        return False, '', 'Inactive (DNS unresolvable / NXDOMAIN)'

    # 2. Check if pointed directly to our server
    if resolved_ip in SERVER_IPS:
        return True, resolved_ip, f'Live on Server ({resolved_ip})'

    # 3. Check if proxied via Cloudflare
    if is_cloudflare_ip(resolved_ip):
        # Test if it responds to HTTP/HTTPS
        try:
            r = requests.head(f'http://{clean_domain}', timeout=3, allow_redirects=True, headers={'User-Agent': 'VoidPanel-Auditor/1.0'})
            if r.status_code < 500:
                return True, resolved_ip, f'Live via Cloudflare ({resolved_ip})'
        except Exception:
            pass
        return False, resolved_ip, f'Inactive (Cloudflare unreachable)'

    # 4. Points to external third-party server (not our server)
    return False, resolved_ip, f'Inactive (External DNS: {resolved_ip})'

def check_email_status(email_str):
    """
    Performs deep DNS email verification:
    1. RFC structure validation and dummy filter
    2. Domain NS/SOA delegation query
    3. MX record retrieval with RFC 7505 Null-MX rejection
    4. MX host A-record resolution to public, routable IP addresses
    5. SPF (v=spf1) record inspection
    6. DMARC (v=DMARC1) record inspection
    
    Returns (is_verified: bool, message: str)
    """
    if not email_str or not EMAIL_REGEX.match(email_str.strip()):
        return False, 'Unreal / Invalid email format'
    
    email_clean = email_str.strip().lower()
    parts = email_clean.split('@')
    if len(parts) != 2:
        return False, 'Invalid email structure'
    localpart, mail_domain = parts[0], parts[1]

    if localpart in DUMMY_LOCALPARTS or mail_domain in DUMMY_DOMAINS:
        return False, f'Unreal / Dummy email ({mail_domain})'

    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['8.8.8.8', '1.1.1.1']
    resolver.timeout = 2.5
    resolver.lifetime = 2.5

    # 1. NS delegation / domain existence check
    try:
        resolve_q(resolver, mail_domain, 'NS')
    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return False, f'Unreal domain (NXDOMAIN: {mail_domain} does not exist)'
    except Exception:
        # Fallback to SOA
        try:
            resolve_q(resolver, mail_domain, 'SOA')
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            return False, f'Unreal domain (NXDOMAIN: {mail_domain} does not exist)'
        except Exception:
            pass

    # 2. MX Record Deep Inspection
    mx_entries = []
    has_null_mx = False
    try:
        answers = resolve_q(resolver, mail_domain, 'MX')
        for rdata in answers:
            target = str(rdata.exchange).rstrip('.')
            pref = rdata.preference
            if target == '' or target == '.':
                has_null_mx = True
            else:
                mx_entries.append((pref, target))
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        pass
    except Exception:
        pass

    if has_null_mx:
        return False, 'Unverified (Explicitly rejects mail / Null MX RFC 7505)'

    if not mx_entries:
        return False, 'Unverified (No MX records configured)'

    # 3. Resolve MX Target Hostnames to Public IP
    valid_mx_hosts = []
    for pref, target in sorted(mx_entries, key=lambda x: x[0]):
        try:
            a_answers = resolve_q(resolver, target, 'A')
            for a in a_answers:
                ip_str = str(a)
                if not is_bogon_or_private(ip_str):
                    valid_mx_hosts.append((target, ip_str))
                    break
        except Exception:
            continue

    if not valid_mx_hosts:
        first_target = mx_entries[0][1]
        return False, f'Unverified (MX host {first_target} fails IP resolution)'

    primary_target, primary_ip = valid_mx_hosts[0]

    # 4. Check SPF Record
    has_spf = False
    try:
        txt_answers = resolve_q(resolver, mail_domain, 'TXT')
        for rdata in txt_answers:
            txt_content = b"".join(rdata.strings).decode('utf-8', errors='ignore')
            if txt_content.startswith('v=spf1'):
                has_spf = True
                break
    except Exception:
        pass

    # 5. Check DMARC Record
    has_dmarc = False
    try:
        dmarc_answers = resolve_q(resolver, f'_dmarc.{mail_domain}', 'TXT')
        for rdata in dmarc_answers:
            txt_content = b"".join(rdata.strings).decode('utf-8', errors='ignore')
            if 'v=DMARC1' in txt_content:
                has_dmarc = True
                break
    except Exception:
        pass

    signals = [f"MX: {primary_target}"]
    if has_spf:
        signals.append("SPF active")
    if has_dmarc:
        signals.append("DMARC active")

    return True, f"Verified ({', '.join(signals)})"

def audit_single_user(user_obj):
    raw_domain = user_obj.domain
    clean_domain = clean_domain_name(raw_domain)
    
    dom_active, dom_ip, dom_msg = check_domain_status(clean_domain)
    email_verif, email_msg = check_email_status(user_obj.email)
    
    user_obj.is_domain_active = dom_active
    user_obj.domain_ip = dom_ip
    user_obj.domain_status_msg = dom_msg
    user_obj.is_email_verified = email_verif
    user_obj.email_status_msg = email_msg
    user_obj.last_audited_at = timezone.now()
    user_obj.save(update_fields=[
        'is_domain_active', 'domain_ip', 'domain_status_msg',
        'is_email_verified', 'email_status_msg', 'last_audited_at'
    ])
    
    return {
        'username': user_obj.username,
        'domain': raw_domain,
        'domain_active': dom_active,
        'domain_ip': dom_ip,
        'domain_status_msg': dom_msg,
        'email': user_obj.email,
        'email_verified': email_verif,
        'email_status_msg': email_msg,
    }

def audit_all_accounts():
    users = user.objects.all()
    stats = {
        'total': users.count(),
        'domain_active': 0,
        'domain_inactive': 0,
        'email_verified': 0,
        'email_unverified': 0,
    }
    for u in users:
        res = audit_single_user(u)
        if res['domain_active']:
            stats['domain_active'] += 1
        else:
            stats['domain_inactive'] += 1
            
        if res['email_verified']:
            stats['email_verified'] += 1
        else:
            stats['email_unverified'] += 1
            
    return stats
