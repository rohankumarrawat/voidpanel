from django.core.management.base import BaseCommand
from control.auditor import audit_all_accounts, audit_single_user
from control.models import user

class Command(BaseCommand):
    help = 'Audit domain live status and email verification for all VoidPanel accounts'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default=None, help='Audit a specific user only')

    def handle(self, *args, **options):
        username = options.get('username')
        if username:
            self.stdout.write(f"Auditing specific user: {username}...")
            target = user.objects.filter(username=username).first()
            if not target:
                self.stderr.write(f"User {username} not found!")
                return
            res = audit_single_user(target)
            self.stdout.write(
                f"Result: Domain={res['domain']} Live={res['domain_active']} ({res['domain_status_msg']}) | "
                f"Email={res['email']} Verified={res['email_verified']} ({res['email_status_msg']})"
            )
        else:
            self.stdout.write("Starting VoidPanel Domain & Email Audit for all accounts...")
            stats = audit_all_accounts()
            self.stdout.write(self.style.SUCCESS(
                f"Audit Completed Successfully!\n"
                f"Total Accounts: {stats['total']}\n"
                f"Active Domains (Live on Server): {stats['domain_active']}\n"
                f"Inactive Domains (External/Down): {stats['domain_inactive']}\n"
                f"Verified Emails: {stats['email_verified']}\n"
                f"Unverified Emails: {stats['email_unverified']}"
            ))
