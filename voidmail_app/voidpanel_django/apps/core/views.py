from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from apps.mail_engine.models import VirtualDomain, VirtualMailbox

def landing_page(request):
    """Render high-converting public landing page, or sovereign Gmail workspace if logged in."""
    # If logged in as superadmin, redirect directly to the Superadmin Console
    if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
        return redirect('superadmin_dashboard')

    # Normal logged-in client user: show modern Gmail-style workspace (unless ?landing=1 is explicitly passed)
    if request.user.is_authenticated and not request.GET.get('landing'):
        return render(request, 'workspace.html')

    total_domains = VirtualDomain.objects.count()
    total_mailboxes = VirtualMailbox.objects.count()
    context = {
        'total_domains': total_domains,
        'total_mailboxes': total_mailboxes,
    }
    return render(request, 'landing.html', context)

def workspace_view(request):
    """Dedicated Gmail-style workspace endpoint for logged-in clients & admins"""
    if not request.user.is_authenticated:
        return redirect('login')
    return render(request, 'workspace.html')

def signup_view(request):
    """Dedicated modern signup & registration page for VoidOnyx Sovereign Workspace"""
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('superadmin_dashboard')
        return redirect('workspace')
    return render(request, 'signup.html')

def login_view(request):
    """Secure login view with role-based routing"""
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.is_staff:
            return redirect('superadmin_dashboard')
        return redirect('landing_page')

    error = None
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        # Check if user exists by email as well
        user = authenticate(request, username=username, password=password)
        if user is None and '@' in username:
            matched_user = User.objects.filter(email__iexact=username).first()
            if matched_user:
                user = authenticate(request, username=matched_user.username, password=password)

        if user is not None:
            if user.is_active:
                from apps.mail_engine.models import UserTwoFactorProfile
                profile, _ = UserTwoFactorProfile.objects.get_or_create(user=user)
                has_keys = user.security_keys.exists()
                has_whatsapp = bool(profile.whatsapp_number)
                is_2fa_active = profile.is_2fa_enabled and (has_keys or has_whatsapp)

                target_dest = next_url if next_url and next_url != '/login/' else ('superadmin_dashboard' if (user.is_superuser or user.is_staff) else 'workspace')

                if is_2fa_active:
                    import datetime
                    from django.utils import timezone
                    request.session['2fa_pending_user_id'] = user.id
                    request.session['2fa_pending_expiry'] = (timezone.now() + datetime.timedelta(minutes=5)).timestamp()
                    request.session['2fa_next_url'] = target_dest if '/' in target_dest else ('/superadmin/' if (user.is_superuser or user.is_staff) else '/workspace/')
                    return render(request, 'login.html', {
                        'step_2fa': True,
                        'pending_user': user,
                        'keys': user.security_keys.all(),
                        'has_keys': has_keys,
                        'has_whatsapp': has_whatsapp,
                        'whatsapp_hint': profile.whatsapp_number[-4:] if len(profile.whatsapp_number) >= 4 else profile.whatsapp_number,
                        'next': next_url
                    })

                # Normal user without 2FA: direct sign in!
                login(request, user)
                return redirect(target_dest)
            else:
                error = 'Your account has been disabled.'
        else:
            error = 'Invalid username or password. Please try again.'

    return render(request, 'login.html', {'error': error, 'next': next_url})

def logout_view(request):
    """Sign out administrator and clear session"""
    logout(request)
    return redirect('login')

def health_check(request):
    """Health check endpoint for Docker & load balancers"""
    return JsonResponse({
        'status': 'healthy',
        'service': 'VoidOnyx Cloud Workspace',
        'version': '1.0.0'
    })
