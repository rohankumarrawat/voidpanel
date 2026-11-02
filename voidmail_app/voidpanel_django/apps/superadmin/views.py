import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from apps.mail_engine.models import VirtualDomain, VirtualMailbox, VirtualAlias, SystemSetting
from apps.mail_engine.services import MailEngineService
from apps.drive.models import DriveFile
from apps.api.models import ApiKey
from apps.ai_engine.models import HuggingFaceApiKey, CustomDomainAiAccess, UserAiAccess

@login_required(login_url='/login/')
def dashboard_view(request):
    """Superadmin workspace control console (protected by login)"""
    domains = VirtualDomain.objects.all()
    mailboxes = VirtualMailbox.objects.all()
    drive_files = DriveFile.objects.all()
    api_keys = ApiKey.objects.all()
    setting, _ = SystemSetting.objects.get_or_create(primary_domain='voidonyx.com')
    
    custom_ai_domains = CustomDomainAiAccess.objects.all().order_by('-created_at')
    user_ai_records = UserAiAccess.objects.all().order_by('-created_at')
    pending_ai_requests = UserAiAccess.objects.filter(upgrade_requested=True).order_by('-requested_at')

    context = {
        'domains': domains,
        'mailboxes': mailboxes,
        'drive_files': drive_files,
        'api_keys': api_keys,
        'setting': setting,
        'total_domains': domains.count(),
        'total_mailboxes': mailboxes.count(),
        'total_files': drive_files.count(),
        'current_user': request.user,
        'custom_ai_domains': custom_ai_domains,
        'user_ai_records': user_ai_records,
        'pending_ai_requests': pending_ai_requests,
        'pending_ai_count': pending_ai_requests.count(),
    }
    return render(request, 'superadmin/dashboard.html', context)

@login_required(login_url='/login/')
def sync_live_server(request):
    """Bridge endpoint to sync real accounts from fast.voidpanel.com"""
    domain = request.GET.get('domain', 'voidonyx.com')
    remote_host = request.GET.get('host', 'https://fast.voidpanel.com')
    try:
        synced_accounts = MailEngineService.sync_live_accounts(domain_name=domain, remote_host=remote_host)
        return JsonResponse({
            'status': 'success',
            'server': remote_host,
            'domain': domain,
            'accounts': synced_accounts,
            'message': f'Synced {len(synced_accounts)} live accounts from {remote_host}'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required(login_url='/login/')
@csrf_exempt
def create_mailbox_ajax(request):
    """AJAX endpoint to provision a new virtual mailbox"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip().lower()
            password = data.get('password', 'VoidOnyx@2026')
            quota_mb = int(data.get('quota_mb', 5120))
            
            if '@' not in email:
                return JsonResponse({'success': False, 'error': 'Invalid email address'})
            
            username, domain_name = email.split('@', 1)
            success, message, mailbox = MailEngineService.provision_email_account(
                username=username,
                domain_name=domain_name,
                password=password,
                quota_mb=quota_mb
            )
            
            if not success:
                return JsonResponse({'success': False, 'error': message})
            
            return JsonResponse({
                'success': True,
                'email': mailbox.email,
                'quota_mb': mailbox.quota_mb,
                'message': 'Mailbox provisioned successfully on Dovecot/Postfix & fast.voidpanel.com!'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'POST required'})

@login_required(login_url='/login/')
def export_database_json(request):
    """1-Click JSON export of all server records for migration"""
    domains = list(VirtualDomain.objects.values('id', 'name', 'is_verified', 'created_at'))
    mailboxes = list(VirtualMailbox.objects.values('id', 'username', 'email', 'password_hash', 'quota_mb', 'used_mb', 'is_active'))
    aliases = list(VirtualAlias.objects.values('id', 'source_email', 'destination_email', 'is_active'))
    
    export_payload = {
        'version': '1.0.0',
        'exported_at': '2026-09-01T12:00:00Z',
        'server': 'mail.voidpanel.com',
        'domains': domains,
        'mailboxes': mailboxes,
        'aliases': aliases
    }
    
    response = HttpResponse(
        json.dumps(export_payload, indent=2, default=str),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="voidmail_migration_backup.json"'
    return response

@login_required(login_url='/login/')
@csrf_exempt
def update_whatsapp_settings(request):
    """Update WhatsApp API Gateway and Test Mode settings"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})
    
    try:
        data = json.loads(request.body)
        setting, _ = SystemSetting.objects.get_or_create(primary_domain='voidonyx.com')
        
        # Meta WhatsApp Cloud API credentials
        setting.whatsapp_api_url = data.get('whatsapp_api_url', '').strip()
        setting.whatsapp_api_key = data.get('whatsapp_api_key', '').strip()
        setting.whatsapp_sender_id = data.get('whatsapp_sender_id', '').strip()
        if 'whatsapp_phone_number_id' in data:
            setting.whatsapp_phone_number_id = data.get('whatsapp_phone_number_id', '').strip()
        if 'whatsapp_app_id' in data:
            setting.whatsapp_app_id = data.get('whatsapp_app_id', '').strip()
        if 'whatsapp_provider' in data:
            setting.whatsapp_provider = data.get('whatsapp_provider', 'meta').strip()
        if 'whatsapp_alert_template' in data:
            setting.whatsapp_alert_template = data.get('whatsapp_alert_template', 'email_alert_template').strip()

        setting.whatsapp_template = data.get('whatsapp_template', 'otp_template').strip()
        setting.test_mode_enabled = bool(data.get('test_mode_enabled', False))
        if 'default_quota_mb' in data:
            setting.default_quota_mb = int(data.get('default_quota_mb', 5120))
        setting.save()
        return JsonResponse({
            'success': True,
            'message': 'Meta WhatsApp Cloud API Gateway settings saved successfully!',
            'test_mode': setting.test_mode_enabled
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/login/')
@csrf_exempt
def test_whatsapp_api(request):
    """Dispatches a one-time test WhatsApp message (OTP or VIP Email Alert) using configured Meta Cloud API credentials"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body) if request.body else {}
        phone_number = data.get('phone_number', '919354519271').strip()
        test_type = data.get('test_type', 'otp').strip().lower()

        from apps.core.whatsapp import send_meta_whatsapp_otp, send_meta_whatsapp_email_alert, clean_whatsapp_phone
        clean_phone = clean_whatsapp_phone(phone_number)
        setting = SystemSetting.objects.first()

        if test_type in ('email_alert', 'alert', 'email'):
            sender = data.get('sender', 'Sundar Pichai (sundar@google.com)')
            subject = data.get('subject', 'VoidOnyx Enterprise Partnership')
            date_str = data.get('date_str', 'Today at 08:30 PM')
            snippet = data.get('snippet', 'Reviewed the sovereign mail security specs. Ready to proceed with enterprise deployment.')
            
            success, res_data = send_meta_whatsapp_email_alert(
                clean_phone,
                sender=sender,
                subject=subject,
                date_str=date_str,
                snippet=snippet,
                rule_label='SuperAdmin Test',
                setting=setting
            )
            template_used = getattr(setting, 'whatsapp_alert_template', 'email_alert_template') or 'email_alert_template'
            label_msg = "Meta WhatsApp VIP Email Alert"
        else:
            otp_code = data.get('otp_code', '123456').strip()
            success, res_data = send_meta_whatsapp_otp(clean_phone, otp_code, setting=setting)
            template_used = getattr(setting, 'whatsapp_template', 'otp_template') or 'otp_template'
            label_msg = "Meta WhatsApp OTP"

        if success:
            return JsonResponse({
                'success': True,
                'message': f"{label_msg} successfully delivered to +{clean_phone}!",
                'response': res_data,
                'to': clean_phone,
                'test_type': test_type,
                'template': template_used
            })
        else:
            return JsonResponse({
                'success': False,
                'error': res_data.get('error', res_data),
                'to': clean_phone,
                'test_type': test_type,
                'template': template_used,
                'response': res_data
            }, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required(login_url='/login/')
@csrf_exempt
def update_email_sending_limit(request):
    """Update personal outbound sending limit for a specific email address in both Django and Postfix policy daemon"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        limit_val = int(data.get('limit', 100))

        if not email:
            return JsonResponse({'success': False, 'error': 'Email is required'})

        # 1. Update SQLite database of the Postfix rate policy daemon (/var/lib/voidpanel-mail-policy/rate.db)
        db_path = '/var/lib/voidpanel-mail-policy/rate.db'
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=5)
            conn.execute('CREATE TABLE IF NOT EXISTS user_limits (username TEXT PRIMARY KEY, limit_val INTEGER, timespan INTEGER)')
            if limit_val > 0:
                conn.execute('INSERT OR REPLACE INTO user_limits (username, limit_val, timespan) VALUES (?, ?, 3600)', (email, limit_val))
            else:
                conn.execute('DELETE FROM user_limits WHERE username=?', (email,))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Policy DB Update Error]: {e}")

        # 2. Update Django VirtualMailbox model
        mb = VirtualMailbox.objects.filter(email__iexact=email).first()
        if mb:
            mb.hourly_limit = limit_val
            mb.save()

        return JsonResponse({
            'success': True,
            'message': f'Sending rate limit for {email} updated to {limit_val} emails/hour!',
            'email': email,
            'limit': limit_val
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='/login/')
@csrf_exempt
def update_global_sending_limit(request):
    """Update global default outbound sending limit for all accounts"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
        limit_val = int(data.get('global_limit', 100))
        setting, _ = SystemSetting.objects.get_or_create(primary_domain='voidonyx.com')
        setting.global_hourly_limit = limit_val
        setting.save()

        # Update /etc/voidpanel-mail-policy.conf
        conf_path = '/etc/voidpanel-mail-policy.conf'
        try:
            with open(conf_path, 'w') as f:
                f.write(f"hourly_limit={limit_val}\n")
        except Exception as e:
            print(f"[Global Conf Update Error]: {e}")

        return JsonResponse({
            'success': True,
            'message': f'Global sending limit updated to {limit_val} emails/hour!',
            'global_limit': limit_val
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from apps.ai_engine.models import HuggingFaceApiKey
from apps.ai_engine.hf_service import ensure_default_keys, ROUTER_URL
import urllib.request, ssl

@login_required(login_url='/login/')
def get_hf_keys_ajax(request):
    """List all configured Hugging Face API keys with stats"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    ensure_default_keys()
    keys = list(HuggingFaceApiKey.objects.all().values(
        'id', 'api_key', 'label', 'model_name', 'is_active', 'usage_count', 'error_count', 'last_used', 'last_error', 'created_at'
    ))
    # Mask API key for security
    for k in keys:
        raw = k['api_key']
        k['masked_key'] = f"{raw[:7]}...{raw[-6:]}" if len(raw) > 13 else raw
    return JsonResponse({'success': True, 'keys': keys})

@login_required(login_url='/login/')
@csrf_exempt
def add_hf_key_ajax(request):
    """Add a new Hugging Face API key"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    try:
        data = json.loads(request.body)
        api_key = data.get('api_key', '').strip()
        label = data.get('label', '').strip() or 'HF Key'
        model_name = data.get('model_name', 'meta-llama/Llama-3.1-8B-Instruct').strip()

        if not api_key:
            return JsonResponse({'success': False, 'error': 'API key is required'})

        obj, created = HuggingFaceApiKey.objects.update_or_create(
            api_key=api_key,
            defaults={'label': label, 'model_name': model_name, 'is_active': True}
        )
        return JsonResponse({
            'success': True,
            'message': f'Hugging Face API key for {label} saved successfully!',
            'created': created
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='/login/')
@csrf_exempt
def delete_hf_key_ajax(request):
    """Delete a Hugging Face API key"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        key_id = data.get('id')
        HuggingFaceApiKey.objects.filter(id=key_id).delete()
        return JsonResponse({'success': True, 'message': 'API key deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='/login/')
@csrf_exempt
def toggle_hf_key_ajax(request):
    """Toggle active status of a Hugging Face API key"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        key_id = data.get('id')
        k = HuggingFaceApiKey.objects.get(id=key_id)
        k.is_active = not k.is_active
        k.save()
        return JsonResponse({'success': True, 'is_active': k.is_active})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required(login_url='/login/')
@csrf_exempt
def test_hf_key_ajax(request):
    """Test a Hugging Face API key with a live completion test"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        key_id = data.get('id')
        k = HuggingFaceApiKey.objects.get(id=key_id)
        ctx = ssl._create_unverified_context()
        payload = json.dumps({
            'model': k.model_name or 'meta-llama/Llama-3.1-8B-Instruct',
            'messages': [{'role': 'user', 'content': 'Say "VoidOnyx AI operational" in 4 words.'}],
            'max_tokens': 20
        }).encode('utf-8')
        req = urllib.request.Request(
            ROUTER_URL,
            data=payload,
            headers={'Authorization': f'Bearer {k.api_key}', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            reply = res['choices'][0]['message']['content'].strip()
            return JsonResponse({'success': True, 'message': f'Connection verified: "{reply}"'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/login/')
@csrf_exempt
def update_ai_auto_approve_setting(request):
    """Toggle master switch for auto-approving AI features on custom domains"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        auto_approve = bool(data.get('auto_approve', True))
        setting = SystemSetting.objects.first()
        if not setting:
            setting = SystemSetting.objects.create(primary_domain='voidonyx.com')
        setting.ai_auto_approve_new_users = auto_approve
        setting.save(update_fields=['ai_auto_approve_new_users', 'updated_at'])
        return JsonResponse({
            'success': True,
            'auto_approve': setting.ai_auto_approve_new_users,
            'message': f"✓ AI Auto-Approve set to {'ON (New custom domains automatically get AI)' if auto_approve else 'OFF (Custom domains require admin approval)'}"
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/login/')
def list_ai_access_api(request):
    """Retrieve all AI access records, custom domains, and pending upgrade requests"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    setting = SystemSetting.objects.first()
    domains = [d.to_dict() for d in CustomDomainAiAccess.objects.all().order_by('-created_at')]
    users = [u.to_dict() for u in UserAiAccess.objects.all().order_by('-created_at')]
    pending = [u.to_dict() for u in UserAiAccess.objects.filter(upgrade_requested=True).order_by('-requested_at')]
    return JsonResponse({
        'success': True,
        'auto_approve': setting.ai_auto_approve_new_users if setting else True,
        'free_domain': setting.ai_free_default_domain if setting else 'voidonyx.com',
        'domains': domains,
        'users': users,
        'pending_requests': pending
    })


@login_required(login_url='/login/')
@csrf_exempt
def approve_domain_ai_api(request):
    """Whitelist or toggle AI access for an entire custom domain"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        domain = data.get('domain', '').strip().lower().replace('http://', '').replace('https://', '').split('/')[0]
        if not domain or '.' not in domain:
            return JsonResponse({'success': False, 'error': 'Valid domain name required (e.g. acme.com)'}, status=400)
        is_enabled = bool(data.get('is_ai_enabled', True))
        plan_name = data.get('plan_name', 'Pro AI')
        notes = data.get('notes', '')

        dom_obj, created = CustomDomainAiAccess.objects.get_or_create(
            domain=domain,
            defaults={
                'is_ai_enabled': is_enabled,
                'plan_name': plan_name,
                'approved_by': request.user,
                'notes': notes
            }
        )
        if not created:
            dom_obj.is_ai_enabled = is_enabled
            if plan_name: dom_obj.plan_name = plan_name
            if notes: dom_obj.notes = notes
            dom_obj.approved_by = request.user
            dom_obj.save()

        return JsonResponse({
            'success': True,
            'message': f"✓ Domain {domain} AI access set to {'Enabled' if is_enabled else 'Disabled'}",
            'domain': dom_obj.to_dict()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/login/')
@csrf_exempt
def approve_user_ai_api(request):
    """Approve or toggle AI access for a specific user email"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        is_enabled = bool(data.get('is_ai_enabled', True))
        status = 'active' if is_enabled else 'locked'

        from django.contrib.auth.models import User
        user_obj = User.objects.filter(email__iexact=email).first() or request.user

        user_acc, _ = UserAiAccess.objects.get_or_create(
            user=user_obj,
            email=email,
            defaults={
                'is_ai_enabled': is_enabled,
                'status': status,
                'approved_by': request.user
            }
        )
        user_acc.is_ai_enabled = is_enabled
        user_acc.status = status
        user_acc.upgrade_requested = False
        user_acc.approved_by = request.user
        user_acc.save()

        return JsonResponse({
            'success': True,
            'message': f"✓ User {email} AI status set to {status}",
            'user_access': user_acc.to_dict()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required(login_url='/login/')
@csrf_exempt
def handle_upgrade_request_api(request):
    """1-Click approve or dismiss an AI upgrade request"""
    if not (request.user.is_superuser or request.user.is_staff):
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        record_id = data.get('record_id') or data.get('request_id')
        action = data.get('action', 'approve')

        rec = get_object_or_404(UserAiAccess, id=record_id)
        if action == 'approve':
            rec.is_ai_enabled = True
            rec.status = 'active'
            rec.upgrade_requested = False
            rec.approved_by = request.user
            rec.save()
            domain = rec.email.split('@')[-1]
            CustomDomainAiAccess.objects.get_or_create(
                domain=domain,
                defaults={'is_ai_enabled': True, 'plan_name': 'Pro AI', 'approved_by': request.user}
            )
            msg = f"✓ Approved AI Pro access for {rec.email} (and @{domain})!"
        else:
            rec.upgrade_requested = False
            rec.save()
            msg = f"Dismissed upgrade request for {rec.email}."

        return JsonResponse({'success': True, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
