"""
panel/middleware.py — LicenseMiddleware

Intercepts every request and redirects to /activate/ if the panel
does not have a valid active license from voidpanel.com.
"""
from django.shortcuts import redirect

_EXEMPT_PREFIXES = (
    "/activate/",
    "/static/",
    "/favicon.ico",
    "/admin/",
    "/api/license/",     # License validation — must work before activation
    "/api/provision/",   # Provisioning bridge — called by portal website
    "/api/v2/ping/",     # Public ping — no auth required
    "/autologin/",       # SSO auto-login from voidpanel.com client portal
    "/license/",         # License management page — always reachable
)


class LicenseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip license check for exempt paths
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return self.get_response(request)

        # Lazy import to avoid circular imports at startup
        from control.license import is_licensed  # noqa: PLC0415
        if not is_licensed():
            return redirect("/activate/")

        return self.get_response(request)
