"""
VoidPanel / VoidOnyx Domain-Based Routing Middleware
Detects which site is being requested and sets:
  - request.site_id = 'voidonyx' | 'voidpanel'
  - request.is_voidonyx = True | False
  - request.is_india = True | False
  - request.currency_symbol = '₹' | '$'
  - request.currency_code = 'INR' | 'USD'
  - request.currency_rate = 1 | <INR-to-USD rate>
Also sets thread-local so the template loader can pick the right templates dir.

Environment override:
  FORCE_SITE=voidonyx   → always serve VoidOnyx (useful for running on a separate port)
  FORCE_SITE=voidpanel  → always serve VoidPanel
"""

import os
from voidonyx.template_loader import set_current_site

VOIDONYX_HOSTS = {
    'voidonyx.com',
    'www.voidonyx.com',
    'voidonyx.in',
    'www.voidonyx.in',
    'voidonyx.local',
    'www.voidonyx.local',
}

# INR → USD conversion rate (update periodically or fetch from API)
INR_TO_USD_RATE = 0.012  # 1 INR ≈ $0.012

# Read once at startup for performance
_FORCE_SITE = os.environ.get('FORCE_SITE', '').lower().strip()


class SiteMiddleware:
    """
    Sets `request.site_id` = 'voidonyx' | 'voidpanel'
    Also sets `request.is_voidonyx`, `request.is_india`, and currency attributes.

    Priority:
      1. FORCE_SITE env var (overrides site selection — but still reads hostname for currency)
      2. Hostname matching
      3. Default → VoidPanel
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower().split(':')[0]  # strip port

        # ── 1. Environment override (FORCE_SITE=voidonyx) ──────────────────
        if _FORCE_SITE == 'voidonyx':
            request.site_id = 'voidonyx'
            request.is_voidonyx = True
            # Only show USD on .com — everything else (localhost, .in) defaults to INR
            request.is_india = not host.endswith('.com')
            set_current_site('voidonyx')

        # ── 2. Hostname-based detection ─────────────────────────────────────
        elif host in VOIDONYX_HOSTS:
            request.site_id = 'voidonyx'
            request.is_voidonyx = True
            request.is_india = host.endswith('.in')
            set_current_site('voidonyx')

        else:
            # Default: VoidPanel (covers localhost, 127.0.0.1, voidpanel.com)
            request.site_id = 'voidpanel'
            request.is_voidonyx = False
            request.is_india = True  # VoidPanel is INR-only
            set_current_site('voidpanel')

        # ── Set currency based on is_india ──────────────────────────────────
        if request.is_india:
            request.currency_symbol = '₹'
            request.currency_code = 'INR'
            request.currency_rate = 1  # Prices stored in INR
        else:
            request.currency_symbol = '$'
            request.currency_code = 'USD'
            request.currency_rate = INR_TO_USD_RATE

        response = self.get_response(request)
        return response


