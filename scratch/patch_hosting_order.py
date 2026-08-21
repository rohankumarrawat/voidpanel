#!/usr/bin/env python3
"""Add HostingOrder.save() hook for new purchase WhatsApp alert."""

MODELS_PATH = '/home/voidonyx/voidonyx/data/models.py'

with open(MODELS_PATH, 'r') as f:
    content = f.read()

old = '''    def __str__(self):
        return f"Order #{self.pk} — {self.user.username} — {self.package.name if self.package else self.package_name}"


class PanelLicenseRecord(models.Model):'''

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


class PanelLicenseRecord(models.Model):'''

if 'new_purchase' in content.split('class HostingOrder')[1].split('class PanelLicenseRecord')[0]:
    print("[SKIP] HostingOrder save hook already exists")
else:
    if old in content:
        content = content.replace(old, new, 1)
        with open(MODELS_PATH, 'w') as f:
            f.write(content)
        print("[OK] Added HostingOrder.save() hook")
    else:
        print("[ERROR] Could not find marker text")

print("HOOK_DONE")
