#!/usr/bin/env python3
"""
Add new_purchase WhatsApp alert hooks to ALL order models on the live server.
Each hook detects status change from pending_payment → paid/active and fires a WA message.
"""

MODELS_PATH = '/home/voidonyx/voidonyx/data/models.py'

with open(MODELS_PATH, 'r') as f:
    content = f.read()

changes = 0

# ── Helper: generates save() hook code for an order model ──
def make_hook(model_name, service_label, name_field, price_field='price'):
    return f'''
    def save(self, *args, **kwargs):
        is_new_purchase = False
        if self.pk:
            old = {model_name}.objects.filter(pk=self.pk).values('status').first()
            if old and old['status'] == 'pending_payment' and self.status in ('paid', 'active', 'provisioning'):
                is_new_purchase = True
        super().save(*args, **kwargs)
        if is_new_purchase:
            try:
                from voidpanel.views import send_whatsapp_notification_async
                msg = (
                    f"\\U0001f389 *New Purchase — {service_label}*\\n"
                    f"Service: {{self.{name_field}}}\\n"
                    f"Amount: \\u20b9{{self.{price_field}}}\\n"
                    f"Thank you for your purchase!\\n"
                    f"Portal: https://voidonyx.in/portal/"
                )
                send_whatsapp_notification_async(self.user, msg, 'new_purchase')
            except Exception as e:
                import logging
                logging.error(f"Error sending WhatsApp {service_label} purchase alert: {{e}}")
'''


# Each entry: (ModelName, __str__ anchor, service_label, name_field, price_field)
orders = [
    ('DomainOrder',      'f"{self.domain_name} ({self.user.username})"',
     'Domain Registration', 'domain_name', 'final_price'),

    ('SSLOrder',         "f'SSLOrder #{self.pk}",
     'SSL Certificate', 'domain', 'price'),

    ('EmailOrder',       "f'EmailOrder #{self.pk}",
     'Email Hosting', 'domain', 'price'),

    ('SuiteOrder',       'f"SuiteOrder #{self.id}',
     'Digital Suite', 'suite', 'price'),

    ('ErpCrmOrder',      'f"ErpCrmOrder #{self.id}',
     'ERP/CRM', 'company_name', 'price'),

    ('GymPortalOrder',   'f"GymPortalOrder #{self.id}',
     'Gym Portal', 'gym_name', 'price'),

    ('AIVoiceOrder',     'f"AIVoiceOrder #{self.id}',
     'AI Voice Calling', 'business_name', 'price'),

    ('HotelPortalOrder', 'f"HotelPortalOrder #{self.id}',
     'Hotel Management', 'hotel_name', 'price'),

    ('KhataBookOrder',   'f"KhataBookOrder #{self.id}',
     'KhataBook', 'business_name', 'price'),

    ('LeadGenOrder',     'f"LeadGenOrder #{self.id}',
     'Lead Generator', 'business_name', 'price'),
]

for model_name, str_marker, label, name_field, price_field in orders:
    # Check if hook already exists
    try:
        section = content.split(f'class {model_name}')[1].split('\nclass ')[0]
    except IndexError:
        print(f"[SKIP] {model_name} — class not found")
        continue

    if 'new_purchase' in section:
        print(f"[SKIP] {model_name} — hook already exists")
        continue

    # Find the __str__ method return line and inject after
    hook_code = make_hook(model_name, label, name_field, price_field)

    # Strategy: inject the save() method right before the next class definition
    # Find the class body end by looking for the __str__ return
    import re
    # We'll insert the hook after the __str__ method
    pattern = f'(class {model_name}.*?def __str__\\(self\\):.*?return .*?\\n)(\\n)'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_pos = match.end(1)
        content = content[:insert_pos] + hook_code + content[insert_pos:]
        changes += 1
        print(f"[OK] {model_name} — added new_purchase hook")
    else:
        print(f"[WARN] {model_name} — could not find insertion point")

with open(MODELS_PATH, 'w') as f:
    f.write(content)

print(f"\nTotal changes: {changes}")
print("ALL_ORDERS_DONE")
