#!/usr/bin/env python3
"""
Patch live server's views.py to replace WhatsApp Web daemon with Cloud API.
Run ON the live server.
"""
import sys

VIEWS_PATH = '/home/voidonyx/voidonyx/voidpanel/views.py'

with open(VIEWS_PATH, 'r') as f:
    content = f.read()

changes = 0

# ── Step 0: Add robots_txt if missing ──
if 'def robots_txt' not in content:
    content += '''

def robots_txt(request):
    from django.http import HttpResponse
    lines = [
        "User-agent: *",
        "Disallow: /portal/",
        "Disallow: /super-admin/",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Allow: /",
    ]
    return HttpResponse("\\n".join(lines), content_type="text/plain")
'''
    changes += 1
    print("[OK] Added robots_txt")

# ── Step 1: Replace _call_wa_api function ──
old_func = 'def _call_wa_api(endpoint, method=\'GET\', payload=None):\n    import urllib.request\n    import json\n    url = f"http://127.0.0.1:3001/{endpoint.lstrip(\'/\')}"'

new_func_full = '''def _send_whatsapp_message(to_phone, message_text):
    """
    Send a text message via the WhatsApp Business Cloud API (Meta Graph API).
    Returns (success: bool, error_message: str).
    """
    import urllib.request
    import urllib.error
    import json
    import re as _re

    try:
        from data.models import WhatsAppConfig
        config = WhatsAppConfig.objects.filter(id=1).first()
    except Exception:
        config = None

    if not config or not config.api_phone_number_id or not config.api_access_token:
        return False, 'WhatsApp API credentials not configured'

    digits = _re.sub(r'[^\\d]', '', to_phone)
    if len(digits) == 10:
        digits = '91' + digits

    api_ver = config.api_version or 'v20.0'
    url = f'https://graph.facebook.com/{api_ver}/{config.api_phone_number_id}/messages'

    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': digits,
        'type': 'text',
        'text': {'preview_url': False, 'body': message_text},
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config.api_access_token}',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode('utf-8'))
            if body.get('messages'):
                return True, ''
            return False, body.get('error', {}).get('message', 'Unknown API response')
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode('utf-8'))
            err_msg = err_body.get('error', {}).get('message', str(exc))
        except Exception:
            err_msg = str(exc)
        import logging
        logging.getLogger('voidpanel').error('WhatsApp Cloud API HTTP error for %s: %s', digits, err_msg)
        return False, err_msg
    except Exception as exc:
        import logging
        logging.getLogger('voidpanel').error('WhatsApp Cloud API error for %s: %s', digits, exc)
        return False, str(exc)'''

if old_func in content:
    # Find the end of the _call_wa_api function
    idx = content.find(old_func)
    # Find the next function definition or class after _call_wa_api
    # The function ends at "return {'ok': False, 'error': str(exc)}" 
    end_marker = "return {'ok': False, 'error': str(exc)}"
    end_idx = content.find(end_marker, idx)
    if end_idx > 0:
        end_idx += len(end_marker)
        content = content[:idx] + new_func_full + content[end_idx:]
        changes += 1
        print("[OK] Replaced _call_wa_api with _send_whatsapp_message")
else:
    print("[SKIP] _call_wa_api already replaced or not found")

# ── Step 2: Replace service view WA send call ──
old_svc = """res = _call_wa_api('send', method='POST', payload={'to': phone, 'message': msg})
            if res.get('ok') or res.get('success'):
                from data.models import WhatsAppLog
                WhatsAppLog.objects.create(
                    user=service.user,
                    phone_to=phone,
                    message=msg,
                    msg_type='alert',
                    status='sent'
                )
                messages.success(request, f"Account info WhatsApp sent to {phone} successfully!")
            else:
                err_msg = res.get('error', 'Daemon error')
                messages.error(request, f"Failed to send WhatsApp: {err_msg}")"""

new_svc = """success, err_msg = _send_whatsapp_message(phone, msg)
            from data.models import WhatsAppLog
            WhatsAppLog.objects.create(
                user=service.user,
                phone_to=phone,
                message=msg,
                msg_type='alert',
                status='sent' if success else 'failed',
                error_msg='' if success else err_msg,
            )
            if success:
                messages.success(request, f"Account info WhatsApp sent to {phone} successfully!")
            else:
                messages.error(request, f"Failed to send WhatsApp: {err_msg}")"""

if old_svc in content:
    content = content.replace(old_svc, new_svc)
    changes += 1
    print("[OK] Updated service view WA send")
else:
    print("[SKIP] Service view WA send not found")

# ── Step 3: Replace super_admin_whatsapp view ──
sa_start_marker = 'def super_admin_whatsapp(request):'
sa_end_marker = "    return render(request, 'super_admin_whatsapp.html', ctx)\n"

idx_start = content.find(sa_start_marker)
idx_end = content.find(sa_end_marker, idx_start)

if idx_start > 0 and idx_end > idx_start:
    idx_end += len(sa_end_marker)
    
    new_sa = '''def super_admin_whatsapp(request):
    denied = _super_admin_guard(request)
    if denied:
        return denied

    from data.models import WhatsAppConfig, WhatsAppLog
    from django.contrib.auth import get_user_model
    User = get_user_model()

    config, created = WhatsAppConfig.objects.get_or_create(id=1)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_settings':
            config.is_enabled = request.POST.get('is_enabled') == 'on'
            config.phone_number = request.POST.get('phone_number', '').strip()
            config.alert_on_invoice_created = request.POST.get('alert_on_invoice_created') == 'on'
            config.alert_on_service_suspend = request.POST.get('alert_on_service_suspend') == 'on'
            config.alert_on_ticket_opened = request.POST.get('alert_on_ticket_opened') == 'on'
            config.save()
            messages.success(request, "WhatsApp integration settings updated successfully.")
            return redirect('/super-admin/whatsapp/')

        elif action == 'update_api_credentials':
            config.api_phone_number_id = request.POST.get('api_phone_number_id', '').strip()
            config.api_waba_id = request.POST.get('api_waba_id', '').strip()
            config.api_access_token = request.POST.get('api_access_token', '').strip()
            config.api_version = request.POST.get('api_version', 'v20.0').strip() or 'v20.0'
            config.save()
            messages.success(request, "WhatsApp Business API credentials saved successfully.")
            return redirect('/super-admin/whatsapp/')

        elif action == 'send_test':
            phone = request.POST.get('phone_number', '').strip()
            message = request.POST.get('message', '').strip()
            if not phone or not message:
                messages.error(request, "Recipient phone and message content are required.")
            else:
                success, err_msg = _send_whatsapp_message(phone, message)
                WhatsAppLog.objects.create(
                    phone_to=phone,
                    message=message,
                    msg_type='alert',
                    status='sent' if success else 'failed',
                    error_msg='' if success else err_msg,
                )
                if success:
                    messages.success(request, f"Test message successfully sent to {phone}!")
                else:
                    messages.error(request, f"Failed to send message: {err_msg}")
            return redirect('/super-admin/whatsapp/')

        elif action == 'broadcast':
            target_group = request.POST.get('target_group')
            message = request.POST.get('message', '').strip()
            if not message:
                messages.error(request, "Broadcast message content is required.")
                return redirect('/super-admin/whatsapp/')

            contacts = []
            users_query = User.objects.filter(is_staff=False, is_superuser=False)

            for u in users_query:
                try:
                    ph = u.customer_profile.phone
                except Exception:
                    ph = None
                if not ph:
                    continue

                if target_group == 'all':
                    contacts.append(u)
                elif target_group == 'unpaid_invoices':
                    from data.models import Invoice
                    if Invoice.objects.filter(user=u, status='unpaid').exists():
                        contacts.append(u)
                elif target_group == 'active_hosting':
                    from data.models import HostingService
                    if HostingService.objects.filter(user=u, status='active').exists():
                        contacts.append(u)

            if not contacts:
                messages.error(request, "No clients found with valid phone numbers in this group.")
                return redirect('/super-admin/whatsapp/')

            phone_list = [c.customer_profile.phone for c in contacts]

            def run_broadcast_async(phones, text, users_map):
                import time
                for ph in phones:
                    ok, err = _send_whatsapp_message(ph, text)
                    usr = users_map.get(ph)
                    WhatsAppLog.objects.create(
                        user=usr,
                        phone_to=ph,
                        message=text,
                        msg_type='broadcast',
                        status='sent' if ok else 'failed',
                        error_msg='' if ok else err,
                    )
                    time.sleep(0.8)

            users_map = {u.customer_profile.phone: u for u in contacts}
            import threading
            threading.Thread(target=run_broadcast_async, args=(phone_list, message, users_map), daemon=True).start()

            messages.success(request, f"Broadcast bulk send triggered for {len(phone_list)} clients in the background.")
            return redirect('/super-admin/whatsapp/')

    # GET
    api_configured = bool(config.api_phone_number_id and config.api_access_token)
    state = 'connected' if api_configured else 'not_configured'

    logs = WhatsAppLog.objects.select_related('user').order_by('-created_at')[:20]

    ctx = _build_super_admin_context('whatsapp')
    ctx.update({
        'config': config,
        'state': state,
        'api_configured': api_configured,
        'logs': logs,
    })
    return render(request, 'super_admin_whatsapp.html', ctx)
'''
    content = content[:idx_start] + new_sa + content[idx_end:]
    changes += 1
    print("[OK] Replaced super_admin_whatsapp view")
else:
    print(f"[SKIP] super_admin_whatsapp not found (start={idx_start}, end={idx_end})")

# ── Step 4: Replace send_whatsapp_notification_async internals ──
old_notif = """res = _call_wa_api('send', method='POST', payload={'to': phone, 'message': message})
        is_ok = res.get('ok') or res.get('success') or False
        WhatsAppLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            phone_to=phone,
            message=message,
            msg_type='alert',
            status='sent' if is_ok else 'failed',
            error_msg='' if is_ok else res.get('error', 'Daemon error')
        )"""

new_notif = """success, err_msg = _send_whatsapp_message(phone, message)
        WhatsAppLog.objects.create(
            user=user if (user and user.is_authenticated) else None,
            phone_to=phone,
            message=message,
            msg_type='alert',
            status='sent' if success else 'failed',
            error_msg='' if success else err_msg,
        )"""

if old_notif in content:
    content = content.replace(old_notif, new_notif)
    changes += 1
    print("[OK] Updated send_whatsapp_notification_async")
else:
    print("[SKIP] send_whatsapp_notification_async already patched")

# Verify no _call_wa_api references remain
remaining = content.count('_call_wa_api')
if remaining > 0:
    print(f"[WARN] {remaining} references to _call_wa_api still remain!")
else:
    print("[OK] No _call_wa_api references remain")

with open(VIEWS_PATH, 'w') as f:
    f.write(content)

print(f"\nTotal changes: {changes}")
print("PATCH_COMPLETE")
