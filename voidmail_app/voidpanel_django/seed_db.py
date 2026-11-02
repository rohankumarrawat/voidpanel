import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel_project.settings')
django.setup()

from django.contrib.auth.models import User
from apps.mail_engine.models import VirtualDomain, VirtualMailbox, VirtualAlias, SystemSetting, EmailSignature, SharedInbox, MailFilterRule
from apps.drive.models import DriveFile
from apps.api.models import ApiKey
from apps.sales_tools.models import EmailTrackingLog, FollowUpSequence, SequenceStep, TextSnippet, SharedThread
from apps.ai_engine.models import AiTaskItem, MorningBriefing
from apps.omnichannel.models import VipContact, OmnichannelLog
from apps.security_shield.models import BurnOnReadMessage, VoidMaskAlias, VaultItem
from apps.collaboration.models import CalendarEvent, BookingSlot, VoidDoc, SignatureDocument, FormDefinition

# 0. Superadmin Administrator Accounts
if not User.objects.filter(username='admin').exists():
    admin_user = User.objects.create_superuser('admin', 'admin@voidonyx.com', 'VoidOnyx@2026#Admin')
    print("✓ Created Superadmin user: admin (Pass: VoidOnyx@2026#Admin)")
else:
    admin_user = User.objects.get(username='admin')
    admin_user.set_password('VoidOnyx@2026#Admin')
    admin_user.save()

if not User.objects.filter(username='voidpanelc091').exists():
    panel_user = User.objects.create_superuser('voidpanelc091', 'voidpanelc091@voidonyx.com', 'jhhj$#$DHJNHJBJHBJH')
    print("✓ Created Panel user: voidpanelc091 (Pass: jhhj$#$DHJNHJBJHBJH)")
else:
    panel_user = User.objects.get(username='voidpanelc091')
    panel_user.set_password('jhhj$#$DHJNHJBJHBJH')
    panel_user.save()

# Purge all non-superadmin accounts (strictly keep only superadmins)
deleted_count = User.objects.filter(is_superuser=False).delete()
if deleted_count[0] > 0:
    print(f"✓ Purged {deleted_count[0]} non-superadmin users.")

# 1. System Settings & Domains
setting, _ = SystemSetting.objects.get_or_create(
    primary_domain='voidonyx.com',
    defaults={
        'master_hostname': 'mail.voidpanel.com', 
        'default_quota_mb': 5120,
        'test_mode_enabled': True
    }
)
d1, _ = VirtualDomain.objects.get_or_create(name='voidonyx.com', is_verified=True)
d2, _ = VirtualDomain.objects.get_or_create(name='voidonyx.info', is_verified=True)

# 2. Virtual Mailboxes (Superadmin only, purge test boxes)
VirtualMailbox.objects.exclude(username__in=['admin', 'voidpanelc091']).delete()

def add_box(domain, username, quota_mb=5120, used_mb=100):
    box, _ = VirtualMailbox.objects.get_or_create(
        domain=domain,
        username=username,
        defaults={'quota_mb': quota_mb, 'used_mb': used_mb}
    )
    box.set_dovecot_password('VoidOnyx@2026#Admin')
    box.save()

add_box(d1, 'admin', 10240, 50)

EmailSignature.objects.get_or_create(
    name='Rohan Rawat - Executive Signature',
    defaults={'html_content': '<strong>Rohan Rawat</strong><br>Founder & Lead Architect, VoidOnyx<br>📱 +91 98765 43210 • 🌐 voidonyx.in', 'is_default': True}
)

SharedInbox.objects.get_or_create(email='support@voidonyx.com', defaults={'name': 'Customer Support Desk'})
SharedInbox.objects.get_or_create(email='sales@voidonyx.com', defaults={'name': 'Sales & Enterprise Inquiries'})

MailFilterRule.objects.get_or_create(
    name='Auto-Tag Invoices',
    defaults={'condition_field': 'subject', 'condition_match': 'Invoice', 'action_type': 'tag', 'action_value': 'Billing'}
)

# 3. Sales Tools
EmailTrackingLog.objects.get_or_create(
    token='trk_demo_alex_99',
    defaults={
        'sender_email': 'rohan@voidonyx.com',
        'recipient_email': 'alex@clientcorp.in',
        'subject': 'Q3 Partnership Agreement & Terms',
        'open_count': 3,
        'first_opened_at': timezone.now(),
        'last_opened_at': timezone.now(),
        'last_ip_address': '103.21.244.0',
        'last_user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    }
)

seq, _ = FollowUpSequence.objects.get_or_create(name='3-Step Cold Enterprise Sequence', defaults={'trigger_condition': 'if_no_reply_in_3_days'})
SequenceStep.objects.get_or_create(sequence=seq, step_number=1, defaults={'delay_days': 3, 'subject': 'Following up on VoidOnyx Proposal', 'body': 'Hi {{first_name}}, wanted to check if you had a chance to review the proposal...'})
SequenceStep.objects.get_or_create(sequence=seq, step_number=2, defaults={'delay_days': 7, 'subject': 'Quick question regarding your email infrastructure', 'body': 'Hey {{first_name}}, are you free for a quick 10-min call Thursday?'})

TextSnippet.objects.get_or_create(shortcut=';pitch', defaults={'title': 'Company Elevator Pitch', 'content': 'VoidOnyx is a sovereign AI business email & cloud workspace that replaces expensive Google Workspace with 80% cost savings.'})
TextSnippet.objects.get_or_create(shortcut=';bank', defaults={'title': 'Bank Wire Details', 'content': 'Bank: HDFC Bank | A/C: 50200012345678 | IFSC: HDFC0001234 | Beneficiary: VoidOnyx Cloud'})

# 4. AI Engine
AiTaskItem.objects.get_or_create(
    task_description='Send revised partnership agreement to Alex',
    defaults={'source_email_subject': 'Q3 Partnership Agreement', 'sender': 'alex@clientcorp.in', 'due_date': '2026-09-03', 'is_completed': False}
)

# 5. Omnichannel (WhatsApp VIP)
VipContact.objects.get_or_create(
    email='ceo@investor.com',
    defaults={'name': 'Mark Investor', 'whatsapp_number': '+919876543210', 'alert_keywords': 'TERM SHEET, URGENT, INVOICE'}
)

# 6. Security Shield
VoidMaskAlias.objects.get_or_create(
    alias_email='shopping.a8b1@voidonyx.in',
    defaults={'real_destination': 'rohan@voidonyx.com', 'label': 'Amazon & Flipkart', 'is_forwarding_active': True}
)

VaultItem.objects.get_or_create(
    title='AWS Root Account',
    defaults={'service_url': 'https://aws.amazon.com', 'username': 'admin@voidonyx.com', 'encrypted_password': 'ENCRYPTED_AES256_HASH_99182a', 'category': 'Cloud'}
)

# 7. Collaboration
BookingSlot.objects.get_or_create(slug='rohan-20min-demo', defaults={'title': '20-Min VoidOnyx Product Walkthrough', 'duration_minutes': 20})
VoidDoc.objects.get_or_create(title='Q3 Product Architecture Roadmap', defaults={'content': '# VoidOnyx Q3 Roadmap\n- Deploy sovereign AI gateway\n- 1-Click Hetzner & Contabo migration'})
SignatureDocument.objects.get_or_create(title='Enterprise Service Level Agreement (SLA)', defaults={'signatory_email': 'alex@clientcorp.in', 'is_signed': False})
FormDefinition.objects.get_or_create(title='Enterprise Pilot Beta Signup Form', defaults={'delivery_email': 'sales@voidonyx.com'})

print("🌟 Full 8-Module Seed Data Populated Successfully!")
