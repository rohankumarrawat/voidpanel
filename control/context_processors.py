"""
VoidPanel — Context Processors

Injects shared context variables into every template:
  - is_reseller / reseller_profile  — reseller mode guard
  - panel_branding                  — white-label branding (PanelBranding singleton)
  - license_tier                    — current license tier slug
  - license_features                — dict of feature flags from PanelLicense
  - white_label_active              — bool: True when white_label is licensed + configured
"""


def reseller_context(request):
    """
    Returns:
        is_reseller (bool)        — True when the logged-in user is an active reseller
        reseller_profile (obj)    — ResellerProfile instance, or None
    """
    if not request.user.is_authenticated:
        return {'is_reseller': False, 'reseller_profile': None}

    # Super admins are never resellers — they have full access
    if request.user.is_superuser:
        return {'is_reseller': False, 'reseller_profile': None}

    try:
        from control.models import ResellerProfile
        profile = ResellerProfile.objects.select_related('auth_user').get(
            auth_user=request.user,
            is_active=True,
        )
        return {'is_reseller': True, 'reseller_profile': profile}
    except Exception:
        pass

    return {'is_reseller': False, 'reseller_profile': None}


def branding_context(request):
    """
    Injects panel branding + license feature flags into every template.

    White-label only activates when:
      1. The license has white_label=True in features_json
      2. AND PanelBranding has been customised (panel_name differs from default)

    If white-label is not licensed, the panel always shows "VoidPanel" branding.
    """
    try:
        from control.models import PanelLicense, PanelBranding
        from control.license import get_features, get_tier

        lic = PanelLicense.objects.first()
        features = get_features()
        tier = get_tier()

        # ── Normalize API key names → template key names ──────────────────────
        # The license API returns keys like 'social_media', 'reseller_hosting',
        # 'docker_manager', 'whatsapp_automation' but templates check for
        # 'social_suite', 'reseller', 'docker', 'whatsapp'.
        _key_map = {
            'social_media':        'social_suite',
            'reseller_hosting':    'reseller',
            'docker_manager':      'docker',
            'whatsapp_automation': 'whatsapp',
        }
        for api_key, template_key in _key_map.items():
            if api_key in features:
                features.setdefault(template_key, features[api_key])
        # ─────────────────────────────────────────────────────────────────────

        white_label_licensed = bool(features.get('white_label', False))

        branding = PanelBranding.get()

        # Only expose custom branding when the license allows it
        if white_label_licensed:
            effective_name   = branding.panel_name or 'VoidPanel'
            effective_logo   = branding.panel_logo_url
            effective_color  = branding.primary_color or '#6366f1'
            effective_fav    = branding.favicon_url
            effective_support = branding.support_url
            hide_badge       = branding.hide_voidpanel_badge
        else:
            effective_name   = 'VoidPanel'
            effective_logo   = ''
            effective_color  = '#6366f1'
            effective_fav    = ''
            effective_support = ''
            hide_badge       = False

        return {
            'panel_name':          effective_name,
            'panel_logo_url':      effective_logo,
            'panel_primary_color': effective_color,
            'panel_favicon_url':   effective_fav,
            'panel_support_url':   effective_support,
            'hide_voidpanel_badge': hide_badge,
            'white_label_active':  white_label_licensed,
            'panel_branding':      branding,
            'license_tier':        tier,
            'license_features':    features,
            'panel_license':       lic,
        }
    except Exception:
        # Never crash on context processors — fall back to defaults
        return {
            'panel_name':          'VoidPanel',
            'panel_logo_url':      '',
            'panel_primary_color': '#6366f1',
            'panel_favicon_url':   '',
            'panel_support_url':   '',
            'hide_voidpanel_badge': False,
            'white_label_active':  False,
            'panel_branding':      None,
            'license_tier':        'starter',
            'license_features':    {},
            'panel_license':       None,
        }
