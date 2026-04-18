from datetime import timedelta
from decimal import Decimal
from smtplib import SMTPException

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail.backends.smtp import EmailBackend
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, redirect
from django.template.defaultfilters import slugify
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from data.models import (
    CustomerProfile,
    HostingService,
    Installed,
    Invoice,
    Message,
    OutboundEmailProfile,
    PortalActivity,
    StaffProfile,
    StaffRole,
    SupportTicket,
    admindocumentation,
    clientdocumentation,
    negative_review,
    positive_review,
    updates,
)


# ─── Serializers ────────────────────────────────────────────────────────────────

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['text', 'date', 'photo']


class AdminDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = admindocumentation
        fields = ['text', 'date', 'link']


class ClientDocSerializer(serializers.ModelSerializer):
    class Meta:
        model = clientdocumentation
        fields = ['text', 'date', 'link']


class InstalledSerializer(serializers.ModelSerializer):
    class Meta:
        model = Installed
        fields = ['ip', 'number']


class UpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = updates
        fields = ['version']


class PositiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = positive_review
        fields = ['review', 'user', 'content']


class NegativeSerializer(serializers.ModelSerializer):
    class Meta:
        model = negative_review
        fields = ['review', 'user', 'category', 'content']


# ─── API Views ──────────────────────────────────────────────────────────────────

@api_view(['POST'])
def positive(request):
    serializer = PositiveSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def negative(request):
    serializer = NegativeSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def latest_messages(request):
    msgs = Message.objects.all().order_by('-date')[:4]
    serializer = MessageSerializer(msgs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def update(request):
    latest = updates.objects.latest('id')
    serializer = UpdateSerializer(latest)
    return Response(serializer.data)


@api_view(['GET'])
def admindocs(request):
    docs = admindocumentation.objects.all().order_by('date')
    serializer = AdminDocSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def clientdocs(request):
    docs = clientdocumentation.objects.all().order_by('date')
    serializer = ClientDocSerializer(docs, many=True)
    return Response(serializer.data)


@api_view(['POST'])
def increment_number(request):
    ip_address = request.data.get('ip')
    installed_obj, _ = Installed.objects.get_or_create(ip=ip_address)
    installed_obj.number += 1
    installed_obj.save()
    serializer = InstalledSerializer(installed_obj)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ─── Page Views ─────────────────────────────────────────────────────────────────

def index(request):
    return render(request, "index.html")


def aboutus(request):
    return render(request, "aboutus.html")


def addemail(request):
    return render(request, "addemail.html")


def ssl(request):
    return render(request, "addssl.html")


def voidpanelinfo(request):
    return render(request, "blogs/voidpanelinfo.html")


def overview(request):
    return render(request, "overview.html")


def db(request):
    return render(request, "db.html")


def chpass(request):
    return render(request, "chpass.html")


def addweb(request):
    return render(request, "addweb.html")


def notifications(request):
    context = {'data': Message.objects.all().order_by('-date')}
    return render(request, "notifications.html", context)


def docs(request):
    return render(request, "docs.html")


def blog(request):
    return render(request, "blog.html")


def blog1(request):
    return render(request, "blogs/blog1.html")


def blog2(request):
    return render(request, "blogs/blog2.html")


def blog3(request):
    return render(request, "blogs/blog3.html")


def blogs(request):
    return render(request, "blogs.html")


def whmcs(request):
    if request.user.is_authenticated:
        return redirect('/portal/')
    return render(request, "whmcs.html")


def whmcs_module(request):
    return render(request, "whmcs.html")


def _invoice_number_for_user(user, offset):
    return f"VP-{user.id or 0:04d}-{offset:03d}"


def _ticket_number_for_user(user, offset):
    return f"VP-TKT-{user.id or 0:04d}-{offset:03d}"


def _generate_username_from_email(email):
    base = email.split('@')[0].strip().lower()
    cleaned = ''.join(char if char.isalnum() else '_' for char in base).strip('_')
    cleaned = cleaned or 'user'
    username = cleaned[:150]
    suffix = 1
    while User.objects.filter(username=username).exists():
        suffix_text = f"_{suffix}"
        username = f"{cleaned[:150 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return username


def _detect_country_from_request(request):
    header_candidates = [
        request.META.get('HTTP_CF_IPCOUNTRY'),
        request.META.get('HTTP_X_VERCEL_IP_COUNTRY'),
        request.META.get('HTTP_CLOUDFRONT_VIEWER_COUNTRY'),
    ]
    for candidate in header_candidates:
        if candidate and candidate not in {'XX', 'T1'}:
            return candidate.upper()

    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    for part in accept_language.split(','):
        language = part.split(';')[0].strip()
        if '-' in language:
            region = language.split('-')[-1].upper()
            if len(region) == 2 and region.isalpha():
                return region
        if '_' in language:
            region = language.split('_')[-1].upper()
            if len(region) == 2 and region.isalpha():
                return region

    return 'IN'


def ensure_default_staff_roles():
    defaults = [
        {
            'name': 'Operations Manager',
            'description': 'Handles infrastructure, client onboarding, and operational escalations.',
            'can_manage_clients': True,
            'can_manage_infrastructure': True,
            'can_manage_support': True,
        },
        {
            'name': 'Billing Manager',
            'description': 'Responsible for invoices, renewals, and payment workflows.',
            'can_manage_clients': True,
            'can_manage_billing': True,
        },
        {
            'name': 'Support Lead',
            'description': 'Owns support queues, priority tickets, and customer communication.',
            'can_manage_support': True,
            'can_manage_clients': True,
        },
        {
            'name': 'Platform Administrator',
            'description': 'Full internal portal access for systems and staff coordination.',
            'can_manage_clients': True,
            'can_manage_billing': True,
            'can_manage_support': True,
            'can_manage_infrastructure': True,
            'can_manage_staff': True,
        },
    ]
    for item in defaults:
        StaffRole.objects.get_or_create(
            slug=slugify(item['name']),
            defaults=item,
        )


def _staff_permissions_summary(role):
    if not role:
        return []
    flags = [
        ('Clients', role.can_manage_clients),
        ('Billing', role.can_manage_billing),
        ('Support', role.can_manage_support),
        ('Infrastructure', role.can_manage_infrastructure),
        ('Staff', role.can_manage_staff),
    ]
    return [label for label, enabled in flags if enabled]


def _ensure_staff_profile(user, role=None, is_portal_admin=False, department='', display_title=''):
    profile, created = StaffProfile.objects.get_or_create(
        user=user,
        defaults={
            'role': role,
            'is_portal_admin': is_portal_admin,
            'department': department,
            'display_title': display_title,
            'last_seen_at': timezone.now(),
        },
    )
    if not created:
        updated_fields = []
        if role and profile.role_id != role.id:
            profile.role = role
            updated_fields.append('role')
        if display_title and profile.display_title != display_title:
            profile.display_title = display_title
            updated_fields.append('display_title')
        if department and profile.department != department:
            profile.department = department
            updated_fields.append('department')
        if profile.is_portal_admin != is_portal_admin:
            profile.is_portal_admin = is_portal_admin
            updated_fields.append('is_portal_admin')
        profile.last_seen_at = timezone.now()
        updated_fields.append('last_seen_at')
        profile.save(update_fields=updated_fields)
    return profile


EMAIL_EVENT_FIELDS = [
    ('send_on_purchase', 'Send mail on purchase'),
    ('send_on_invoice_created', 'Send invoice created mail'),
    ('send_on_payment_received', 'Send payment received mail'),
    ('send_on_service_activated', 'Send service activation mail'),
    ('send_on_service_suspended', 'Send service suspension mail'),
    ('send_on_service_unsuspended', 'Send service reactivation mail'),
    ('send_on_service_terminated', 'Send service termination mail'),
    ('send_on_ticket_opened', 'Send ticket opened mail'),
    ('send_on_ticket_reply', 'Send ticket reply mail'),
    ('send_on_login_success', 'Send login successful mail'),
    ('send_on_password_reset', 'Send password reset mail'),
    ('send_on_account_created', 'Send account created mail'),
    ('send_on_security_alert', 'Send security alert mail'),
    ('send_on_system_update', 'Send system update mail'),
    ('send_on_domain_expiry_warning', 'Send domain expiry warning'),
    ('send_on_ssl_expiry_warning', 'Send SSL expiry warning'),
]

EMAIL_PURPOSE_CHOICES = OutboundEmailProfile.PURPOSE_CHOICES


def _email_permission_summary(profile):
    return [label for field, label in EMAIL_EVENT_FIELDS if getattr(profile, field)]


def _test_email_profile_connection(profile):
    backend = EmailBackend(
        host=profile.smtp_host,
        port=profile.smtp_port,
        username=profile.smtp_username or None,
        password=profile.smtp_password or None,
        use_tls=profile.use_tls,
        use_ssl=profile.use_ssl,
        timeout=10,
    )
    opened = backend.open()
    if not opened:
        raise SMTPException('SMTP server did not accept the connection.')
    backend.close()


def ensure_portal_seed_data(user, profile_defaults=None):
    profile_defaults = profile_defaults or {}
    CustomerProfile.objects.get_or_create(
        user=user,
        defaults={
            'company_name': profile_defaults.get('company_name', ''),
            'phone': profile_defaults.get('phone', ''),
            'country': profile_defaults.get('country', 'India'),
            'city': profile_defaults.get('city', ''),
        },
    )

    today = timezone.localdate()
    now = timezone.now()

    if not user.hosting_services.exists():
        HostingService.objects.bulk_create([
            HostingService(
                user=user,
                service_name='Starter Shared Hosting',
                domain=f"{user.username}.voidpanel.site",
                product_type='Shared Hosting',
                status='active',
                billing_cycle='monthly',
                monthly_price=Decimal('12.00'),
                next_due_date=today + timedelta(days=14),
                server_hostname='in-mum-01.voidpanel.cloud',
                panel_url='https://panel.voidpanel.com',
                storage_gb=25,
                bandwidth_gb=250,
            ),
            HostingService(
                user=user,
                service_name='Managed VPS',
                domain=f"app-{user.username}.voidpanel.site",
                product_type='Managed VPS',
                status='pending',
                billing_cycle='monthly',
                monthly_price=Decimal('49.00'),
                next_due_date=today + timedelta(days=30),
                server_hostname='in-del-02.voidpanel.cloud',
                panel_url='https://panel.voidpanel.com',
                storage_gb=80,
                bandwidth_gb=1500,
            ),
        ])

    if not user.invoices.exists():
        Invoice.objects.bulk_create([
            Invoice(
                user=user,
                invoice_number=_invoice_number_for_user(user, 1),
                description='Starter Shared Hosting',
                status='paid',
                total=Decimal('12.00'),
                currency='USD',
                due_date=today - timedelta(days=15),
                paid_date=today - timedelta(days=13),
            ),
            Invoice(
                user=user,
                invoice_number=_invoice_number_for_user(user, 2),
                description='Managed VPS Setup and First Cycle',
                status='unpaid',
                total=Decimal('49.00'),
                currency='USD',
                due_date=today + timedelta(days=7),
            ),
        ])

    if not user.support_tickets.exists():
        SupportTicket.objects.bulk_create([
            SupportTicket(
                user=user,
                ticket_number=_ticket_number_for_user(user, 1),
                subject='Initial onboarding and DNS review',
                department='Sales',
                priority='medium',
                status='answered',
                last_reply_at=now - timedelta(hours=6),
            ),
            SupportTicket(
                user=user,
                ticket_number=_ticket_number_for_user(user, 2),
                subject='Enable automated backups for VPS',
                department='Technical Support',
                priority='high',
                status='open',
                last_reply_at=now - timedelta(hours=2),
            ),
        ])

    if not user.portal_activities.exists():
        PortalActivity.objects.bulk_create([
            PortalActivity(
                user=user,
                category='account',
                title='Customer account created',
                description='Portal access was enabled and the starter workspace was prepared.',
            ),
            PortalActivity(
                user=user,
                category='billing',
                title='Invoice generated',
                description='A starter hosting invoice is waiting for payment confirmation.',
            ),
            PortalActivity(
                user=user,
                category='support',
                title='Support ticket opened',
                description='Technical support request created for backup configuration.',
            ),
        ])


@login_required(login_url='/login/')
def portal(request):
    ensure_portal_seed_data(request.user)

    profile = request.user.customer_profile
    services = request.user.hosting_services.all().order_by('next_due_date')
    invoices = request.user.invoices.all()
    tickets = request.user.support_tickets.all()
    activities = request.user.portal_activities.all()[:6]

    unpaid_total = invoices.filter(status__in=['unpaid', 'overdue']).aggregate(
        total=Sum('total')
    )['total'] or Decimal('0.00')
    paid_total = invoices.filter(status='paid').aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    active_service = services.filter(status='active').first()
    next_invoice = invoices.filter(status__in=['unpaid', 'overdue']).order_by('due_date').first()
    latest_ticket = tickets.first()
    service_mix = {
        'active': services.filter(status='active').count(),
        'pending': services.filter(status='pending').count(),
        'suspended': services.filter(status='suspended').count(),
    }

    context = {
        'profile': profile,
        'services': services,
        'invoices': invoices[:5],
        'tickets': tickets[:5],
        'activities': activities,
        'active_service': active_service,
        'next_invoice': next_invoice,
        'latest_ticket': latest_ticket,
        'service_mix': service_mix,
        'stats': {
            'active_services': services.filter(status='active').count(),
            'open_tickets': tickets.exclude(status='closed').count(),
            'unpaid_invoices': invoices.filter(status__in=['unpaid', 'overdue']).count(),
            'monthly_spend': services.filter(status='active').aggregate(
                total=Sum('monthly_price')
            )['total'] or Decimal('0.00'),
            'unpaid_total': unpaid_total,
            'paid_total': paid_total,
            'total_services': services.count(),
            'customer_since': profile.created_at,
        },
    }
    return render(request, "portal.html", context)


@login_required(login_url='/login/')
def super_admin_portal(request):
    if not request.user.is_superuser:
        messages.error(request, "Super admin access is required")
        return redirect('/portal/')

    ensure_default_staff_roles()
    _ensure_staff_profile(
        request.user,
        role=StaffRole.objects.filter(can_manage_staff=True).first(),
        is_portal_admin=True,
        display_title='Super Administrator',
        department='Executive',
    )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_role':
            role_name = request.POST.get('role_name', '').strip()
            description = request.POST.get('description', '').strip()
            if not role_name:
                messages.error(request, "Role name is required")
                return redirect('/super-admin/')
            slug = slugify(role_name)
            if StaffRole.objects.filter(slug=slug).exists():
                messages.error(request, "A role with that name already exists")
                return redirect('/super-admin/')
            StaffRole.objects.create(
                name=role_name,
                slug=slug,
                description=description,
                can_manage_clients=bool(request.POST.get('can_manage_clients')),
                can_manage_billing=bool(request.POST.get('can_manage_billing')),
                can_manage_support=bool(request.POST.get('can_manage_support')),
                can_manage_infrastructure=bool(request.POST.get('can_manage_infrastructure')),
                can_manage_staff=bool(request.POST.get('can_manage_staff')),
            )
            messages.success(request, "Staff role created")
            return redirect('/super-admin/')

        if action == 'create_staff':
            name = request.POST.get('staff_name', '').strip()
            email = request.POST.get('staff_email', '').strip().lower()
            password = request.POST.get('staff_password', '')
            role_id = request.POST.get('role_id')
            department = request.POST.get('department', '').strip()
            is_super_admin = bool(request.POST.get('is_super_admin'))
            if not name or not email or not password:
                messages.error(request, "Name, email, and password are required for new staff")
                return redirect('/super-admin/')
            if User.objects.filter(email=email).exists():
                messages.error(request, "That email is already in use")
                return redirect('/super-admin/')
            try:
                validate_password(password)
            except ValidationError as exc:
                for error in exc.messages:
                    messages.error(request, error)
                return redirect('/super-admin/')

            role = StaffRole.objects.filter(id=role_id).first()
            first_name, _, last_name = name.partition(' ')
            username = _generate_username_from_email(email)
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name.strip(),
                    is_staff=True,
                    is_superuser=is_super_admin,
                )
                ensure_portal_seed_data(user, profile_defaults={'country': 'IN'})
                _ensure_staff_profile(
                    user,
                    role=role,
                    is_portal_admin=True,
                    display_title=role.name if role else 'Staff Member',
                    department=department,
                )
                PortalActivity.objects.create(
                    user=user,
                    category='account',
                    title='Staff access provisioned',
                    description='This account was promoted into the internal operations portal.',
                )
            messages.success(request, "Staff account created")
            return redirect('/super-admin/')

        if action == 'update_staff':
            user_id = request.POST.get('user_id')
            role_id = request.POST.get('role_id')
            department = request.POST.get('department', '').strip()
            title = request.POST.get('display_title', '').strip()
            user = User.objects.filter(id=user_id).first()
            role = StaffRole.objects.filter(id=role_id).first()
            if not user:
                messages.error(request, "Staff member not found")
                return redirect('/super-admin/')
            user.is_staff = bool(request.POST.get('is_staff'))
            user.is_superuser = bool(request.POST.get('is_superuser'))
            user.save(update_fields=['is_staff', 'is_superuser'])
            _ensure_staff_profile(
                user,
                role=role,
                is_portal_admin=bool(request.POST.get('is_portal_admin')),
                department=department,
                display_title=title or (role.name if role else 'Staff Member'),
            )
            messages.success(request, f"Updated access for {user.get_full_name() or user.username}")
            return redirect('/super-admin/')

        if action == 'create_email_profile':
            profile_name = request.POST.get('profile_name', '').strip()
            from_email = request.POST.get('from_email', '').strip()
            smtp_host = request.POST.get('smtp_host', '').strip()
            smtp_port = request.POST.get('smtp_port', '').strip() or '587'
            if not profile_name or not from_email or not smtp_host:
                messages.error(request, "Profile name, sender email, and SMTP host are required")
                return redirect('/super-admin/#settings')

            should_be_default = bool(request.POST.get('is_default'))
            if should_be_default:
                OutboundEmailProfile.objects.update(is_default=False)

            email_profile = OutboundEmailProfile.objects.create(
                profile_name=profile_name,
                purpose_category=request.POST.get('purpose_category', 'transactional'),
                from_name=request.POST.get('from_name', '').strip(),
                from_email=from_email,
                reply_to_email=request.POST.get('reply_to_email', '').strip(),
                smtp_host=smtp_host,
                smtp_port=int(smtp_port),
                smtp_username=request.POST.get('smtp_username', '').strip(),
                smtp_password=request.POST.get('smtp_password', ''),
                use_tls=bool(request.POST.get('use_tls')),
                use_ssl=bool(request.POST.get('use_ssl')),
                is_active=bool(request.POST.get('is_active')),
                is_default=should_be_default or not OutboundEmailProfile.objects.exclude(id=0).exists(),
                **{field: bool(request.POST.get(field)) for field, _ in EMAIL_EVENT_FIELDS},
            )
            if not OutboundEmailProfile.objects.exclude(id=email_profile.id).exists():
                email_profile.is_default = True
                email_profile.save(update_fields=['is_default'])
            messages.success(request, "Email profile created")
            return redirect('/super-admin/#settings')

        if action == 'email_profile_action':
            profile = OutboundEmailProfile.objects.filter(id=request.POST.get('profile_id')).first()
            mode = request.POST.get('mode')
            if not profile:
                messages.error(request, "Email profile not found")
                return redirect('/super-admin/#settings')

            if mode == 'make_default':
                OutboundEmailProfile.objects.update(is_default=False)
                profile.is_default = True
                profile.save(update_fields=['is_default'])
                messages.success(request, f"{profile.profile_name} is now the default email profile")
                return redirect('/super-admin/#settings')

            if mode == 'toggle_active':
                profile.is_active = not profile.is_active
                profile.save(update_fields=['is_active'])
                messages.success(request, f"{profile.profile_name} was {'activated' if profile.is_active else 'paused'}")
                return redirect('/super-admin/#settings')

            if mode == 'test_connection':
                try:
                    _test_email_profile_connection(profile)
                    messages.success(request, f"SMTP test connection succeeded for {profile.profile_name}")
                except Exception as exc:
                    messages.error(request, f"SMTP test failed for {profile.profile_name}: {exc}")
                return redirect('/super-admin/#settings')

    staff_users = User.objects.filter(is_staff=True).order_by('first_name', 'username')
    for user in staff_users:
        _ensure_staff_profile(user, is_portal_admin=getattr(getattr(user, 'staff_profile', None), 'is_portal_admin', False))

    staff_profiles = StaffProfile.objects.select_related('user', 'role').filter(user__is_staff=True)
    roles = list(StaffRole.objects.all())
    client_count = User.objects.filter(is_staff=False, is_superuser=False).count()
    open_ticket_count = SupportTicket.objects.exclude(status='closed').count()
    unpaid_total = Invoice.objects.filter(status__in=['unpaid', 'overdue']).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    monthly_revenue = HostingService.objects.filter(status='active').aggregate(total=Sum('monthly_price'))['total'] or Decimal('0.00')

    recent_clients = User.objects.filter(is_staff=False).order_by('-date_joined')[:6]
    recent_tickets = SupportTicket.objects.select_related('user').all()[:6]
    email_profiles = OutboundEmailProfile.objects.all()
    super_admin_count = staff_profiles.filter(user__is_superuser=True).count()
    portal_admin_count = staff_profiles.filter(is_portal_admin=True).count()
    billing_role_count = StaffRole.objects.filter(can_manage_billing=True).count()
    support_role_count = StaffRole.objects.filter(can_manage_support=True).count()

    for profile in staff_profiles:
        profile.permission_summary = _staff_permissions_summary(profile.role)
    for email_profile in email_profiles:
        email_profile.permission_summary = _email_permission_summary(email_profile)
    email_profiles_by_purpose = {}
    for value, label in EMAIL_PURPOSE_CHOICES:
        bucket = [profile for profile in email_profiles if profile.purpose_category == value]
        if bucket:
            email_profiles_by_purpose[label] = bucket

    context = {
        'email_event_fields': EMAIL_EVENT_FIELDS,
        'email_purpose_choices': EMAIL_PURPOSE_CHOICES,
        'email_profiles': email_profiles,
        'email_profiles_by_purpose': email_profiles_by_purpose,
        'roles': roles,
        'staff_profiles': staff_profiles,
        'recent_clients': recent_clients,
        'recent_tickets': recent_tickets,
        'admin_stats': {
            'staff_count': staff_profiles.count(),
            'role_count': len(roles),
            'client_count': client_count,
            'open_ticket_count': open_ticket_count,
            'monthly_revenue': monthly_revenue,
            'unpaid_total': unpaid_total,
            'super_admin_count': super_admin_count,
            'portal_admin_count': portal_admin_count,
            'billing_role_count': billing_role_count,
            'support_role_count': support_role_count,
        },
    }
    return render(request, 'super_admin.html', context)


def loginn(request):
    if request.user.is_authenticated:
        return redirect("/portal/")
    if request.method == 'POST':
        identity = request.POST.get('Email', '').strip()
        password = request.POST.get('password')
        user = authenticate(request, username=identity, password=password)
        if user is None and identity:
            matched_user = User.objects.filter(email__iexact=identity).first()
            if matched_user:
                user = authenticate(request, username=matched_user.username, password=password)
        if user is not None:
            login(request, user)
            PortalActivity.objects.create(
                user=user,
                category='account',
                title='User logged in',
                description='Accessed the portal successfully.',
            )
            if user.is_superuser:
                return redirect('/super-admin/')
            return redirect('/portal/')
        else:
            messages.error(request, "Invalid username/email or password")
            return redirect('/login/')
    return render(request, "login.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("/portal/")
    if request.method == 'POST':
        email = request.POST.get('Email', '').strip().lower()
        full_name = request.POST.get('full_name', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not full_name or not email:
            messages.error(request, "Please complete your name and email")
            return render(request, 'register.html')
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, 'register.html')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return render(request, 'register.html')
        try:
            validate_password(password)
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            return render(request, 'register.html')

        name_parts = [part for part in full_name.split() if part]
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        username = _generate_username_from_email(email)
        country = _detect_country_from_request(request)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        ensure_portal_seed_data(
            user,
            profile_defaults={
                'country': country,
            },
        )
        login(request, user)
        messages.success(request, "Your client portal is ready")
        return redirect("/portal/")
    return render(request, 'register.html')


def logout_view(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('/')
