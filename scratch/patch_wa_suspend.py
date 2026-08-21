#!/usr/bin/env python3
"""
Patch live server views.py to add WhatsApp suspension alerts at view-level
for cases where .update() bypasses model save().
"""

VIEWS_PATH = '/home/voidonyx/voidonyx/voidpanel/views.py'

with open(VIEWS_PATH, 'r') as f:
    content = f.read()

changes = 0

# 1. suspend_all in super_admin_clients
old1 = """        if action == 'suspend_all':
            uid = request.POST.get('user_id')
            HostingService.objects.filter(user_id=uid, status='active').update(status='suspended')
            messages.success(request, 'All active services for that client have been suspended.')"""

new1 = """        if action == 'suspend_all':
            uid = request.POST.get('user_id')
            suspended_svcs = list(HostingService.objects.filter(user_id=uid, status='active'))
            HostingService.objects.filter(user_id=uid, status='active').update(status='suspended')
            if suspended_svcs:
                suspended_user = suspended_svcs[0].user
                domains = ', '.join(s.domain for s in suspended_svcs[:5])
                msg = f"\\U0001f6ab *Service Suspended*\\nYour hosting services ({domains}) have been suspended due to unpaid invoices.\\nPlease clear pending payments to restore access.\\nPortal: https://voidonyx.in/portal/"
                send_whatsapp_notification_async(suspended_user, msg, 'service_suspend')
            messages.success(request, 'All active services for that client have been suspended.')"""

if old1 in content:
    content = content.replace(old1, new1)
    changes += 1
    print("[OK] Added WA alert to suspend_all")
else:
    print("[SKIP] suspend_all not found")

# 2. manual_suspend in auto-suspend
old2 = """                messages.success(request, f'Service {svc.domain} suspended.')
            return redirect('/super-admin/auto-suspend/')

        elif action == 'manual_unsuspend':"""

# Find the manual_suspend block more precisely
marker2 = "title=f'Service manually suspended: {svc.domain}',"
if marker2 in content and 'send_whatsapp_notification_async(svc.user, msg, \'service_suspend\')' not in content.split(marker2)[1][:500]:
    # Insert after the PortalActivity creation and before messages.success
    old_block = """                messages.success(request, f'Service {svc.domain} suspended.')
            return redirect('/super-admin/auto-suspend/')"""
    new_block = """                msg = f"\\U0001f6ab *Service Suspended*\\nYour hosting service ({svc.domain}) has been suspended.\\nPlease clear pending payments to restore access.\\nPortal: https://voidonyx.in/portal/"
                send_whatsapp_notification_async(svc.user, msg, 'service_suspend')
                messages.success(request, f'Service {svc.domain} suspended.')
            return redirect('/super-admin/auto-suspend/')"""
    content = content.replace(old_block, new_block, 1)
    changes += 1
    print("[OK] Added WA alert to manual_suspend")
else:
    print("[SKIP] manual_suspend already patched or not found")

# 3. suspend_suite
old3 = """                _call_suite_toggle_status(service, is_active=False)
                messages.success(request, f"Suite service '{service.service_name}' suspended successfully.")"""

new3 = """                _call_suite_toggle_status(service, is_active=False)
                msg = f"\\U0001f6ab *Service Suspended*\\nYour suite service ({service.service_name}) has been suspended.\\nPlease clear pending payments to restore access.\\nPortal: https://voidonyx.in/portal/"
                send_whatsapp_notification_async(service.user, msg, 'service_suspend')
                messages.success(request, f"Suite service '{service.service_name}' suspended successfully.")"""

if old3 in content:
    content = content.replace(old3, new3)
    changes += 1
    print("[OK] Added WA alert to suspend_suite")
else:
    print("[SKIP] suspend_suite not found")

# 4. suspend_erp
old4 = """                svc.status = 'suspended'
                svc.save(update_fields=['status'])
                messages.success(request, f'ERP workspace "{svc.company_name}" suspended.')"""

new4 = """                svc.status = 'suspended'
                svc.save(update_fields=['status'])
                msg = f"\\U0001f6ab *Service Suspended*\\nYour ERP workspace ({svc.company_name}) has been suspended.\\nPlease clear pending payments to restore access.\\nPortal: https://voidonyx.in/portal/"
                send_whatsapp_notification_async(svc.user, msg, 'service_suspend')
                messages.success(request, f'ERP workspace "{svc.company_name}" suspended.')"""

if old4 in content:
    content = content.replace(old4, new4)
    changes += 1
    print("[OK] Added WA alert to suspend_erp")
else:
    print("[SKIP] suspend_erp not found")

with open(VIEWS_PATH, 'w') as f:
    f.write(content)

print(f"\nTotal changes: {changes}")
print("PATCH_DONE")
