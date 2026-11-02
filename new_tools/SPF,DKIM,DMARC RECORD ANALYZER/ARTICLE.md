---
title: "Stopping Email Spoofing: A Master Guide to Implementing SPF, DKIM, and DMARC Alignment"
meta_title: "Master Guide: Stop Email Spoofing with SPF, DKIM & DMARC"
meta_description: "Learn how to stop email spoofing and phishing using SPF, DKIM, and DMARC alignment. Complete technical breakdown, commands, and code samples."
slug: "stopping-email-spoofing-spf-dkim-dmarc-guide"
target_keywords:
  - "SPF DKIM DMARC guide"
  - "stop email spoofing"
  - "DMARC alignment explained"
  - "RFC 7208 10 lookup limit"
  - "email authentication technical guide"
internal_link_suggestions:
  - anchor: "email security audit tool"
    url: "/tools/spf-dkim-dmarc-analyzer"
  - anchor: "DNS record troubleshooting guide"
    url: "/blog/dns-record-troubleshooting"
  - anchor: "configuring enterprise mail gateways"
    url: "/blog/enterprise-mail-gateways"
external_references:
  - title: "RFC 7208 - Sender Policy Framework (SPF)"
    url: "https://datatracker.ietf.org/doc/html/rfc7208"
  - title: "RFC 6376 - DomainKeys Identified Mail (DKIM)"
    url: "https://datatracker.ietf.org/doc/html/rfc6376"
  - title: "RFC 7489 - DMARC Specification"
    url: "https://datatracker.ietf.org/doc/html/rfc7489"
  - title: "dmarc.org - Deployment Guidelines"
    url: "https://dmarc.org"
---

# Stopping Email Spoofing: A Master Guide to Implementing SPF, DKIM, and DMARC Alignment

## 1. Introduction & The Core Vulnerability of SMTP

Simple Mail Transfer Protocol (SMTP), designed in RFC 821 in 1982, was built on an implicit trust model. SMTP provides no native authentication mechanism to verify that the domain listed in an email's `From:` header matches the server that transmitted the message.

In a standard SMTP transaction, two distinct sender identities exist:
1. **Envelope Sender (`MAIL FROM` / RFC 5321)**: Transmitted during the initial SMTP handshake (`HELO`/`EHLO`). Bounces and Non-Delivery Reports (NDRs) are routed here.
2. **Header Sender (`From:` / RFC 5322)**: Displayed to the end user inside their email client (e.g. `From: CEO <ceo@example.com>`).

```
+-----------------------------------------------------------------------+
| SMTP Envelope (RFC 5321)                                              |
| MAIL FROM: <spoofer@malicious-attacker.net>                          |
|                                                                       |
| +-------------------------------------------------------------------+ |
| | Message Header (RFC 5322)                                         | |
| | From: "Executive Director" <ceo@target-company.com>              | |
| | Subject: Urgent Wire Transfer                                     | |
| +-------------------------------------------------------------------+ |
+-----------------------------------------------------------------------+
```

Because receiving Mail Transfer Agents (MTAs) historically evaluated only the payload text, bad actors could connect to any open relay, pass `MAIL FROM: <spoofer@malicious.com>`, but inject `From: ceo@target-company.com` into the header.

To eliminate this vulnerability, the internet engineering community introduced three interlocking standards:
* **SPF (Sender Policy Framework - RFC 7208)**: Authorizes IP addresses.
* **DKIM (DomainKeys Identified Mail - RFC 6376)**: Cryptographically signs message contents.
* **DMARC (Domain-based Message Authentication - RFC 7489)**: Enforces identity alignment between RFC 5321 and RFC 5322 senders, defining receiver policy for failures.

---

## 2. Sender Policy Framework (SPF) & The 10-DNS-Lookup Limit

### How SPF Operates
SPF allows a domain owner to publish a list of IP addresses or subnets authorized to send email on behalf of their domain apex. This is published as a DNS `TXT` record at the root domain starting with `v=spf1`.

When a receiving MTA accepts an inbound connection, it extracts the connecting IP address and checks the sender's RFC 5321 `MAIL FROM` domain against its published SPF record.

```
v=spf1 ip4:198.51.100.14/32 include:_spf.google.com include:sendgrid.net -all
```

### SPF Mechanism & Qualifier Syntax
* **Qualifiers**:
  * `+` (Pass - default if omitted): Authorizes matching IPs.
  * `-` (Fail / HardFail): Declares matching IPs explicitly unauthorized.
  * `~` (SoftFail): Indicates unauthorized IPs should be accepted but flagged.
  * `?` (Neutral): Specifies no assertion.

* **Mechanisms**:
  * `ip4` / `ip6`: Direct IP address or CIDR notation (no DNS lookup required).
  * `a`: Authorizes host IP resolved from the domain's A/AAAA records.
  * `mx`: Authorizes host IPs resolved from the domain's MX records.
  * `include:<domain>`: Triggers a recursive SPF lookup on the target domain.
  * `redirect=<domain>`: Replaces the current SPF evaluation with the target domain's SPF record.
  * `all`: Terminal match mechanism.

### The RFC 7208 §4.6.4 10-DNS-Lookup Limit
To protect receiving email servers against Distributed Denial of Service (DDoS) amplification attacks, RFC 7208 §4.6.4 mandates that any SPF evaluation MUST NOT result in more than **10 total DNS lookups**.

Mechanisms that increment the lookup counter:
`include`, `a`, `mx`, `ptr`, `exists`, `redirect`.

> [!WARNING]
> If an SPF record evaluation exceeds 10 lookups, receiving MTAs instantly abort evaluation and return an **SPF PermError**. In strict email receivers (such as Gmail, Microsoft 365, and Yahoo), a PermError results in hard delivery failure or immediate quarantine.

Modern enterprises using multiple cloud services (Salesforce, HubSpot, SendGrid, Zendesk, Google Workspace) frequently exceed this cap when chaining nested `include:` directives.

[SCREENSHOT: tool homepage]

### SPF Inspection Code Implementation
Below is the recursive lookup counter algorithm built into our analyzer tool (`server/services/dnsAnalyzer.js`), which traces nested SPF includes and enforces the 10-lookup threshold:

```javascript
// Excerpt from server/services/dnsAnalyzer.js
export async function analyzeSpf(domain) {
  const issues = [];
  const lookupTree = [];
  let totalLookups = 0;
  const visitedDomains = new Set();

  async function traceSpf(targetDomain, currentDepth = 0) {
    if (visitedDomains.has(targetDomain.toLowerCase())) {
      issues.push(`Circular SPF inclusion detected for domain "${targetDomain}".`);
      return { domain: targetDomain, record: null, circular: true };
    }
    visitedDomains.add(targetDomain.toLowerCase());

    const txtRecords = await resolveTxtWithTimeout(targetDomain);
    const spfRecords = txtRecords.filter((r) => r.toLowerCase().startsWith('v=spf1'));

    if (spfRecords.length === 0) return { domain: targetDomain, record: null };

    const record = spfRecords[0];
    const parsed = parseSpfMechanisms(record);

    const node = { domain: targetDomain, record, mechanismsCounted: [], children: [] };

    for (const mech of parsed.mechanisms) {
      if (['include', 'a', 'mx', 'ptr', 'exists', 'redirect'].includes(mech.type)) {
        totalLookups++;
        node.mechanismsCounted.push({ type: mech.type, raw: mech.raw, lookupIndex: totalLookups });

        if ((mech.type === 'include' || mech.type === 'redirect') && mech.target) {
          if (currentDepth < 5) {
            const childNode = await traceSpf(mech.target, currentDepth + 1);
            node.children.push(childNode);
          }
        }
      }
    }
    return node;
  }

  const tree = await traceSpf(domain);
  lookupTree.push(tree);

  if (totalLookups > 10) {
    issues.push(`RFC 7208 Cap Violation: SPF record generated ${totalLookups} DNS lookups (RFC limit is 10).`);
  }

  return { found: Boolean(tree.record), lookupCount: totalLookups, issues, lookupTree };
}
```

---

## 3. DomainKeys Identified Mail (DKIM) Cryptography & Key Rotation

### How DKIM Works
DKIM provides end-to-end cryptographic authenticity and message integrity using public-key cryptography (RSA or Ed25519).

1. **Signing**: The sending MTA computes a cryptographic hash of selected email headers (including `From`, `To`, `Subject`, `Date`) and the message body (`bh=` body hash). It signs this hash using its **private key** and attaches a `DKIM-Signature` header to the email.
2. **Verification**: The receiving MTA extracts the signature selector (`s=`) and signing domain (`d=`), queries DNS TXT at `<selector>._domainkey.<domain>`, retrieves the **public key**, and decrypts the signature to verify integrity.

```
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
 d=example.com; s=s202601;
 h=from:to:subject:date:message-id;
 bh=47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=;
 b=K3z9...[Base64 Signature Payload]...
```

### Selector Architecture & DNS Publishing
Because a domain may send email through multiple systems simultaneously, DKIM uses **selectors** (`s=`) to allow multiple distinct public keys to co-exist under the same domain without DNS collision.

DNS Query Location: `selector._domainkey.example.com`

Example Public Key TXT Record:
```
v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzV1...
```

### Key Revocation & Key Rotation
Per RFC 6376 §6.1.2, setting `p=` (an empty public key value) revokes the selector, signaling to all receiving MTAs that the key has been invalidated:
```
v=DKIM1; p=
```

#### Key Rotation Best Practice:
1. Generate new key pair (e.g. selector `s2026Q3`).
2. Publish public key for `s2026Q3` to DNS.
3. Update sending MTAs to sign with `s2026Q3`.
4. Keep old selector `s2026Q2` published in DNS for at least 7 days to allow in-flight mail to resolve.
5. Deprecate `s2026Q2` by publishing `p=` (revocation) or removing the TXT record.

---

## 4. DMARC Architecture & Identifier Alignment

### What DMARC Solves
Neither SPF nor DKIM independently requires the authenticated domain to match the visible `From:` header domain displayed to human end-users. An attacker could pass SPF using their own authorized server (`MAIL FROM: attacker.net`) while displaying `From: CEO <ceo@victim.com>`.

DMARC solves this by introducing **Identifier Alignment**.

[SCREENSHOT: sample analysis result for a well-configured domain]

### DMARC Policy Tags (`v=DMARC1`)
Published as a TXT record at `_dmarc.example.com`:
* `p=none`: Monitoring mode. Receivers log authentication failures but deliver messages normally.
* `p=quarantine`: Receivers deliver failing emails to Spam/Junk folders.
* `p=reject`: Receivers outright reject failing emails at the SMTP connection stage (550 rejection).
* `rua=mailto:dmarc-reports@example.com`: Destination URI for daily XML aggregate feedback reports.
* `ruf=mailto:dmarc-failures@example.com`: Destination URI for immediate forensic failure samples.
* `pct=100`: Percentage of messages subjected to policy enforcement (1-100).
* `adkim` / `aspf`: Alignment mode for DKIM and SPF (`r` = relaxed, `s` = strict).

### Strict vs. Relaxed Identifier Alignment

| Mode | Configuration Tag | Description | Example Match Condition |
| :--- | :--- | :--- | :--- |
| **Relaxed SPF** | `aspf=r` (default) | Envelope domain & `From` domain share organizational apex | `mail.example.com` aligns with `example.com` |
| **Strict SPF** | `aspf=s` | Envelope domain & `From` domain must match **exactly** | `mail.example.com` fails strict alignment with `example.com` |
| **Relaxed DKIM**| `adkim=r` (default)| DKIM `d=` domain & `From` domain share organizational apex | `d=sub.example.com` aligns with `example.com` |
| **Strict DKIM** | `adkim=s` | DKIM `d=` domain & `From` domain must match **exactly** | `d=sub.example.com` fails strict alignment with `example.com` |

To pass DMARC, a message MUST pass **either** SPF (with alignment) **or** DKIM (with alignment).

### DMARC Parser Code Implementation
Here is our DMARC parser from `server/services/dnsAnalyzer.js`:

```javascript
// Excerpt from server/services/dnsAnalyzer.js
export function parseDmarcRecord(recordText = '') {
  const raw = String(recordText).trim();
  const issues = [];

  if (!raw.toLowerCase().startsWith('v=dmarc1')) {
    issues.push('DMARC record does not start with compulsory "v=DMARC1" prefix.');
  }

  const tags = {};
  const parts = raw.split(';').map((p) => p.trim()).filter(Boolean);
  for (const part of parts) {
    const eqIdx = part.indexOf('=');
    if (eqIdx !== -1) {
      tags[part.slice(0, eqIdx).trim().toLowerCase()] = part.slice(eqIdx + 1).trim();
    }
  }

  const policy = (tags.p || 'none').toLowerCase();
  const adkim = (tags.adkim || 'r').toLowerCase() === 's' ? 'strict' : 'relaxed';
  const aspf = (tags.aspf || 'r').toLowerCase() === 's' ? 'strict' : 'relaxed';
  const rua = (tags.rua || '').split(',').map((u) => u.trim()).filter(Boolean);

  if (policy === 'none') {
    issues.push('POLICY WARNING: DMARC policy is set to "p=none" (monitoring mode). Emails failing authentication will NOT be rejected.');
  }
  if (rua.length === 0) {
    issues.push('REPORTING WARNING: No aggregate report URI (rua=) configured.');
  }

  return { found: true, record: raw, policy, alignment: { spf: aspf, dkim: adkim }, rua, issues };
}
```

---

## 5. Recommended Rollout Strategy: Monitoring to Rejection

Enforcing DMARC without prior monitoring is the #1 cause of self-inflicted email outages. Third-party SaaS tools sending mail on your behalf will fail authentication if not explicitly configured.

```
       Phase 1                    Phase 2                    Phase 3
 ┌─────────────────┐        ┌──────────────────┐       ┌─────────────────┐
 │   p=none        │  ───►  │   p=quarantine   │  ──►  │   p=reject      │
 │  (Monitoring)   │        │  (Soft Enforce)  │       │ (Full Protect)  │
 └─────────────────┘        └──────────────────┘       └─────────────────┘
    Collect RUA                Remediation                Zero Spoofing
    Reports for                Subdomains &                Allowed at
    30-90 Days                 Cloud Vendors               MTA Level
```

1. **Phase 1: Discovery & Monitoring (`p=none`)**
   Publish `v=DMARC1; p=none; rua=mailto:dmarc-rua@example.com`. Maintain for 30–90 days. Ingest RUA XML reports to index all authorized sending IPs and third-party SaaS tools.
2. **Phase 2: Partial Enforcement (`p=quarantine; pct=25` -> `pct=100`)**
   Configure DKIM keys and SPF records across all discovered vendors. Move to `p=quarantine; pct=100`. Non-aligned emails are routed to Spam folders.
3. **Phase 3: Full Protection (`p=reject`)**
   Promote policy to `v=DMARC1; p=reject; rua=mailto:dmarc-rua@example.com`. Un-authenticated spoofed mail is rejected at the SMTP boundary.

---

## 6. Hands-on Diagnostic Terminal Commands

Sysadmins can run these terminal commands to inspect live DNS records and verify mail server connectivity:

### Querying SPF Records
```bash
dig TXT example.com +short
```

### Querying DMARC Records
```bash
dig TXT _dmarc.example.com +short
```

### Querying DKIM Selectors
```bash
dig TXT google._domainkey.example.com +short
```

### Inspecting DKIM Public Key Length with OpenSSL
```bash
# Extract public key Base64 from TXT output and pipe to OpenSSL
echo "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAzV1..." | base64 -d | openssl rsa -pubin -inform DER -text -noout
```

### Testing Mail Server Reachability (Port 25)
```bash
# Verify MX reachability via netcat / nc
nc -zv mail.example.com 25

# Nmap port scan on SMTP interfaces
nmap -p 25,587 -sV mail.example.com
```

---

## 7. Actionable Troubleshooting Guide

[SCREENSHOT: recursive SPF lookup tree]

### Issue 1: SPF Over 10-Lookup Cap (PermError)
* **Symptom**: Inbound mail soft-fails; DMARC reports show `SPF PermError`. Analyzer shows `lookupCount: 12`.
* **Root Cause**: Excessive nested `include:` directives (e.g. Google + Salesforce + SendGrid + HubSpot + Zendesk).
* **Solution**:
  1. Replace `a` and `mx` mechanisms with static `ip4:` / `ip6:` ranges where vendor IPs are static.
  2. Implement dynamic SPF flattening (resolving include trees to flat IP list updated via cron).
  3. Move transactional marketing tools to dedicated subdomains (e.g. `mail.example.com`).

### Issue 2: DKIM Signature Verification Failure Post-Key-Rotation
* **Symptom**: Receivers report `dkim=fail (bad signature)`.
* **Root Cause**: Old selector TXT record was deleted from DNS before sending MTAs switched to the new private key, or DNS TTL caching delayed record propagation.
* **Solution**: Maintain overlapping selector publication in DNS for at least 7 days before revoking old keys.

### Issue 3: DMARC Alignment Failure on Third-Party SaaS
* **Symptom**: Third-party mailer (e.g., Mailchimp) passes SPF/DKIM under its own domain (`mailchimpapp.com`), but fails DMARC alignment against `From: news@example.com`.
* **Root Cause**: Envelope domain (`MAIL FROM`) is `bounces.mailchimp.com` which does not align with `From: example.com`.
* **Solution**: Configure custom authenticated domain in vendor tool (e.g. custom CNAME pointing `sub.example.com` to vendor host) to align DKIM `d=` and SPF `MAIL FROM`.

### Issue 4: Missing SPF Record Update for New Email Vendor
* **Symptom**: Legitimate transactional emails (e.g. password resets) land in Spam after onboarding a new SaaS platform.
* **Root Cause**: New vendor IP range was omitted from the root SPF record.
* **Solution**: Audit new SaaS deployments against the central SPF record and add vendor `include:` directive before turning on production mail routing.
