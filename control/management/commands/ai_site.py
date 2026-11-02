"""
VoidPanel CLI: AI Site Management Command
Usage:
  python manage.py ai_site list
  python manage.py ai_site show --domain example.com
  python manage.py ai_site generate --domain example.com --name "TechCorp" --desc "AI automation firm" [--theme modern_dark]
  python manage.py ai_site edit --domain example.com --prompt "Add pricing cards with 3 tiers"
  python manage.py ai_site publish --domain example.com
  python manage.py ai_site rollback --domain example.com --version 1
  python manage.py ai_site export --domain example.com [--output /path/to/site.html]
  python manage.py ai_site pool
"""

import sys
from django.core.management.base import BaseCommand, CommandError
from control.models import AISiteProject, AISiteRevision, GeminiAPIKey
from control.gemini_pool import GeminiPoolManager
from control.ai_site_builder import (
    generate_initial_website,
    iterate_website,
    rollback_website,
    publish_website_to_domain
)


class Command(BaseCommand):
    help = "Manage, generate, iterate, and publish AI websites from the CLI"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Subcommand to execute')

        # Subcommand: list
        subparsers.add_parser('list', help='List all AI-generated site projects')

        # Subcommand: show
        show_p = subparsers.add_parser('show', help='Show detailed info about an AI site project')
        show_p.add_argument('--domain', required=True, help='Domain name')

        # Subcommand: generate
        gen_p = subparsers.add_parser('generate', help='Generate a new AI website')
        gen_p.add_argument('--domain', required=True, help='Domain name')
        gen_p.add_argument('--name', required=True, help='Business name')
        gen_p.add_argument('--desc', required=True, help='Business description and highlights')
        gen_p.add_argument('--category', default='Business', help='Business category (default: Business)')
        gen_p.add_argument('--theme', default='modern_dark', help='Theme (modern_dark, clean_light, luxury_gold, ocean_blue)')
        gen_p.add_argument('--user', default='', help='VoidPanel tenant username (default: domain owner)')

        # Subcommand: edit
        edit_p = subparsers.add_parser('edit', help='Iteratively edit an existing AI website using natural language')
        edit_p.add_argument('--domain', required=True, help='Domain name')
        edit_p.add_argument('--prompt', required=True, help='Modification instructions for AI')

        # Subcommand: publish
        pub_p = subparsers.add_parser('publish', help='Publish website to production /home/<user>/public_html/index.html')
        pub_p.add_argument('--domain', required=True, help='Domain name')
        pub_p.add_argument('--user', default='', help='VoidPanel tenant username')

        # Subcommand: rollback
        rb_p = subparsers.add_parser('rollback', help='Rollback to a previous revision')
        rb_p.add_argument('--domain', required=True, help='Domain name')
        rb_p.add_argument('--version', type=int, required=True, help='Revision version number')

        # Subcommand: export
        exp_p = subparsers.add_parser('export', help='Export HTML of an AI website')
        exp_p.add_argument('--domain', required=True, help='Domain name')
        exp_p.add_argument('--output', default='', help='File path to write HTML to (prints to stdout if omitted)')

        # Subcommand: pool
        subparsers.add_parser('pool', help='Show Gemini API Key Pool status and health')

    def handle(self, *args, **options):
        action = options.get('action')
        if not action:
            self.print_help('manage.py', 'ai_site')
            return

        method = getattr(self, f"handle_{action}", None)
        if not method:
            raise CommandError(f"Unknown action: {action}")
        method(options)

    def handle_list(self, options):
        projects = AISiteProject.objects.all().order_by('-created_at')
        if not projects.exists():
            self.stdout.write(self.style.WARNING("No AI site projects found."))
            return

        self.stdout.write("\n" + "=" * 90)
        self.stdout.write(f"{'DOMAIN':<30} {'BUSINESS':<25} {'VER':<5} {'PUBLISHED':<12} {'UPDATED'}")
        self.stdout.write("-" * 90)
        for p in projects:
            pub_str = "YES" if p.is_published else "NO"
            pub_style = self.style.SUCCESS if p.is_published else self.style.WARNING
            up_str = p.updated_at.strftime('%Y-%m-%d %H:%M') if p.updated_at else '-'
            self.stdout.write(f"{p.domain:<30} {p.business_name[:24]:<25} v{p.version:<4} {pub_style(pub_str):<12} {up_str}")
        self.stdout.write("=" * 90 + "\n")

    def handle_show(self, options):
        domain = options['domain']
        project = AISiteProject.objects.filter(domain=domain).first()
        if not project:
            raise CommandError(f"No AI site project found for domain: {domain}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"  AI Site Project: {project.domain}"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Business:   {project.business_name} ({project.business_category})")
        self.stdout.write(f"Theme:      {project.primary_theme}")
        self.stdout.write(f"Version:    v{project.version}")
        self.stdout.write(f"Published:  {'YES (' + str(project.published_at) + ')' if project.is_published else 'NO'}")
        self.stdout.write(f"HTML Size:  {len(project.current_html):,} characters")
        self.stdout.write(f"Owner:      {project.user_identifier}")

        revisions = project.revisions.all().order_by('-version')[:10]
        if revisions:
            self.stdout.write("\nRecent Revisions:")
            for r in revisions:
                self.stdout.write(f"  v{r.version} [{r.created_at.strftime('%Y-%m-%d %H:%M')}]: {r.prompt_used[:60]}")
        self.stdout.write("=" * 60 + "\n")

    def handle_generate(self, options):
        domain = options['domain']
        name = options['name']
        desc = options['desc']
        cat = options['category']
        theme = options['theme']
        user = options['user']

        if not user:
            from control.models import user as ControlUser
            u_obj = ControlUser.objects.filter(domain=domain).first()
            if u_obj and u_obj.username:
                user = u_obj.username
            else:
                user = 'admin'

        self.stdout.write(self.style.NOTICE(f"🤖 Generating AI website for '{name}' ({domain}) using Gemini Pool..."))
        try:
            project, html = generate_initial_website(
                business_name=name,
                category=cat,
                description=desc,
                theme=theme,
                domain_name=domain,
                user_identifier=user
            )
            self.stdout.write(self.style.SUCCESS(f"✅ Website generated successfully!"))
            self.stdout.write(f"  - Version: v{project.version}")
            self.stdout.write(f"  - Size: {len(html):,} characters")
            self.stdout.write(f"  - Web Studio: https://fast.voidpanel.com:8082/control/ai-builder/{domain}/")
            self.stdout.write(f"  - To publish now: python manage.py ai_site publish --domain {domain}")
        except Exception as e:
            raise CommandError(f"Generation failed: {e}")

    def handle_edit(self, options):
        domain = options['domain']
        prompt = options['prompt']

        project = AISiteProject.objects.filter(domain=domain).first()
        if not project:
            raise CommandError(f"No existing AI site project for {domain}. Generate one first.")

        self.stdout.write(self.style.NOTICE(f"✏️  Applying AI edit to {domain} (v{project.version})..."))
        self.stdout.write(f"Prompt: {prompt}")

        try:
            project, updated_html = iterate_website(project.id, prompt)
            self.stdout.write(self.style.SUCCESS(f"✅ Website updated successfully to v{project.version}!"))
            self.stdout.write(f"  - New Size: {len(updated_html):,} characters")
            self.stdout.write(f"  - To publish now: python manage.py ai_site publish --domain {domain}")
        except Exception as e:
            raise CommandError(f"Iteration failed: {e}")

    def handle_publish(self, options):
        domain = options['domain']
        user = options['user']

        project = AISiteProject.objects.filter(domain=domain).first()
        if not project:
            raise CommandError(f"No AI site project found for domain: {domain}")

        if not user:
            from control.models import user as ControlUser
            u_obj = ControlUser.objects.filter(domain=domain).first()
            if u_obj and u_obj.username:
                user = u_obj.username
            else:
                user = project.user_identifier or 'admin'

        self.stdout.write(self.style.NOTICE(f"🚀 Publishing AI website to production (/home/{user}/public_html/index.html)..."))
        try:
            ok, msg = publish_website_to_domain(project, user)
            if ok:
                self.stdout.write(self.style.SUCCESS(f"✅ {msg}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ {msg}"))
        except Exception as e:
            raise CommandError(f"Publish failed: {e}")

    def handle_rollback(self, options):
        domain = options['domain']
        version = options['version']

        project = AISiteProject.objects.filter(domain=domain).first()
        if not project:
            raise CommandError(f"No AI site project found for domain: {domain}")

        self.stdout.write(self.style.NOTICE(f"⏪ Rolling back {domain} to v{version}..."))
        try:
            project, html = rollback_website(project.id, version)
            self.stdout.write(self.style.SUCCESS(f"✅ Rolled back to v{version} (now recorded as v{project.version})!"))
        except Exception as e:
            raise CommandError(f"Rollback failed: {e}")

    def handle_export(self, options):
        domain = options['domain']
        out_path = options['output']

        project = AISiteProject.objects.filter(domain=domain).first()
        if not project:
            raise CommandError(f"No AI site project found for domain: {domain}")

        if out_path:
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(project.current_html)
            self.stdout.write(self.style.SUCCESS(f"Exported HTML ({len(project.current_html):,} bytes) to {out_path}"))
        else:
            sys.stdout.write(project.current_html)

    def handle_pool(self, options):
        from django.utils import timezone
        keys = list(GeminiAPIKey.objects.all().order_by('-created_at'))
        now = timezone.now()

        total = len(keys)
        active = sum(1 for k in keys if k.is_active)
        cooldown = sum(1 for k in keys if k.cooldown_until and k.cooldown_until > now)
        today_req = sum(k.daily_request_count for k in keys)
        all_req = sum(k.total_request_count for k in keys)
        rate_limits = sum(k.rate_limit_hits for k in keys)

        health = 0
        if total > 0:
            healthy = sum(1 for k in keys if k.is_active and not (k.cooldown_until and k.cooldown_until > now))
            health = int((healthy / total) * 100)

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS(f"  Google Gemini API Key Pool Status — Health: {health}%"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total Keys:        {total}")
        self.stdout.write(f"Active Keys:       {active}")
        self.stdout.write(f"In Cooldown:       {cooldown}")
        self.stdout.write(f"Requests Today:    {today_req}")
        self.stdout.write(f"Lifetime Calls:    {all_req}")
        self.stdout.write(f"Rate Limit Hits:   {rate_limits}")
        self.stdout.write("-" * 80)
        self.stdout.write(f"{'LABEL':<20} {'MODEL':<20} {'STATUS':<12} {'TODAY':<8} {'TOTAL':<8} {'429s'}")
        self.stdout.write("-" * 80)
        for k in keys:
            if not k.is_active:
                st = self.style.ERROR("DISABLED")
            elif k.cooldown_until and k.cooldown_until > now:
                st = self.style.WARNING("COOLDOWN")
            else:
                st = self.style.SUCCESS("READY")
            self.stdout.write(f"{k.label[:19]:<20} {k.model_name:<20} {st:<21} {k.daily_request_count:<8} {k.total_request_count:<8} {k.rate_limit_hits}")
        self.stdout.write("=" * 80 + "\n")
