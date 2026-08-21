#!/usr/bin/env python3
"""
Deploy new_purchase alert: patch views.py, models.py, and create migration on server.
"""
import os

# --- 1. Patch models.py: Add alert_on_new_purchase field ---
MODELS_PATH = '/home/voidonyx/voidonyx/data/models.py'
with open(MODELS_PATH, 'r') as f:
    content = f.read()

if 'alert_on_new_purchase' not in content:
    content = content.replace(
        "    alert_on_ticket_opened    = models.BooleanField(default=True)",
        "    alert_on_ticket_opened    = models.BooleanField(default=True)\n    alert_on_new_purchase     = models.BooleanField(default=True)"
    )
    print("[OK] Added alert_on_new_purchase to WhatsAppConfig model")
else:
    print("[SKIP] alert_on_new_purchase already in model")

# --- 2. Add HostingOrder.save() hook ---
if 'class HostingOrder' in content and 'new_purchase' not in content:
    old = '''    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — {self.package.name if self.package else self.package_name}"


class PanelLicenseRecord'''

    new = '''    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — {self.package.name if self.package else self.package_name}"

    def save(self, *args, **kwargs):
        is_new_purchase = False
        if self.pk:
            old = HostingOrder.objects.filter(pk=self.pk).values('status').first()
            if old and old['status'] == 'pending_payment' and self.status in ('paid', 'active', 'provisioning'):
                is_new_purchase = True
        super().save(*args, **kwargs)
        if is_new_purchase:
            try:
                from voidpanel.views import send_whatsapp_notification_async
                pkg_name = self.package.name if self.package else self.package_name
                msg = (
                    f"\\U0001f389 *New Purchase Activated*\\n"
                    f"Package: {pkg_name}\\n"
                    f"Domain: {self.domain}\\n"
                    f"Amount: \\u20b9{self.total}\\n"
                    f"Thank you for your purchase!\\n"
                    f"Portal: https://voidonyx.in/portal/"
                )
                send_whatsapp_notification_async(self.user, msg, 'new_purchase')
            except Exception as e:
                import logging
                logging.error(f"Error sending WhatsApp new purchase alert: {e}")


class PanelLicenseRecord'''

    if old in content:
        content = content.replace(old, new)
        print("[OK] Added HostingOrder.save() hook for new_purchase")
    else:
        print("[WARN] Could not find HostingOrder marker")
else:
    print("[SKIP] HostingOrder hook already exists or not found")

with open(MODELS_PATH, 'w') as f:
    f.write(content)

# --- 3. Patch views.py: Add new_purchase alert check ---
VIEWS_PATH = '/home/voidonyx/voidonyx/voidpanel/views.py'
with open(VIEWS_PATH, 'r') as f:
    vcontent = f.read()

changes = 0

# Add new_purchase check in send_whatsapp_notification_async
if "alert_type == 'new_purchase'" not in vcontent:
    vcontent = vcontent.replace(
        "        if alert_type == 'ticket_opened' and not config.alert_on_ticket_opened:\n            return",
        "        if alert_type == 'ticket_opened' and not config.alert_on_ticket_opened:\n            return\n        if alert_type == 'new_purchase' and not config.alert_on_new_purchase:\n            return"
    )
    changes += 1
    print("[OK] Added new_purchase check in notification function")

# Add saving of new_purchase checkbox
if "alert_on_new_purchase" not in vcontent:
    vcontent = vcontent.replace(
        "            config.alert_on_ticket_opened = request.POST.get('alert_on_ticket_opened') == 'on'\n            config.save()",
        "            config.alert_on_ticket_opened = request.POST.get('alert_on_ticket_opened') == 'on'\n            config.alert_on_new_purchase = request.POST.get('alert_on_new_purchase') == 'on'\n            config.save()"
    )
    changes += 1
    print("[OK] Added alert_on_new_purchase saving in view")

with open(VIEWS_PATH, 'w') as f:
    f.write(vcontent)

print(f"\nViews changes: {changes}")
print("DEPLOY_PATCH_DONE")
