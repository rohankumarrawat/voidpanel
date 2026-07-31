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


class MarketingTenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path.strip('/')
        parts = path.split('/')

        domain = None

        # 1. Path contains domain directly: control/marketing/<domain>/...
        if len(parts) >= 3 and parts[0] == 'control' and parts[1] == 'marketing':
            domain = parts[2]
        # 2. Suite mode: control/suite/... - resolve domain from session
        elif len(parts) >= 2 and parts[0] == 'control' and parts[1] == 'suite':
            su = request.session.get('suite_user')
            if su and su.get('hosting_domain'):
                domain = su.get('hosting_domain')

        if domain:
            from control.models import user as CustomUser, SuiteSubscription
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                # 1. Look up hosting user
                custom_usr = CustomUser.objects.filter(domain=domain).first()
                if custom_usr:
                    owner_user = User.objects.get(username=custom_usr.username)
                    request.user = owner_user
                else:
                    # 2. Look up standalone suite subscription owner
                    sub = SuiteSubscription.objects.filter(hosting_domain=domain).first()
                    if not sub:
                        # Fallback to check prefix matching
                        sub = SuiteSubscription.objects.filter(email__startswith=domain + '@').first()
                    if sub:
                        username = f"suite_{sub.id}"
                        usr, _ = User.objects.get_or_create(
                            username=username,
                            defaults={'email': sub.email, 'is_active': True}
                        )
                        request.user = usr
            except Exception:
                pass

        return self.get_response(request)


class SessionNameFallbackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_superuser:
            if 'name' not in request.session or not request.session['name']:
                request.session['name'] = request.user.username

        return self.get_response(request)

class EnsureCsrfCookieMiddleware:
    """
    1. Force-set the CSRF cookie on every response for authenticated users.
    2. Inject a tiny JS snippet into HTML pages that makes ``fetch()`` and
       ``XMLHttpRequest`` automatically include the ``X-CSRFToken`` header.

    This lets us safely remove ``@csrf_exempt`` from browser-facing views
    without touching any existing templates.
    """

    # The injected script reads the csrftoken cookie and patches both
    # XMLHttpRequest.open and window.fetch to add the header automatically.
    _CSRF_JS = b"""<script data-csrf-helper>
(function(){
  function gc(n){var m=document.cookie.match('(^|;)\\\\s*'+n+'=([^;]+)');return m?m[2]:null}
  var _xo=XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open=function(){_xo.apply(this,arguments);
    var t=gc('csrftoken');if(t)this.setRequestHeader('X-CSRFToken',t);};
  if(window.fetch){var _f=window.fetch;window.fetch=function(u,o){
    o=o||{};o.headers=o.headers||{};var t=gc('csrftoken');
    if(t&&!o.headers['X-CSRFToken'])o.headers['X-CSRFToken']=t;
    return _f.call(this,u,o);};}
  if(window.jQuery||window.$){var jq=window.jQuery||window.$;
    jq.ajaxSetup({beforeSend:function(x,s){
      if(!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(s.type)){
        var t=gc('csrftoken');if(t)x.setRequestHeader('X-CSRFToken',t);}}});}
})();
</script>"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Force CSRF cookie for every authenticated user
        if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
            from django.middleware.csrf import get_token
            get_token(request)  # forces cookie creation

            # Inject JS helper into HTML pages (only if not streaming)
            ct = response.get('Content-Type', '')
            if 'text/html' in ct and not getattr(response, 'streaming', False):
                content = response.content
                # Insert before </head> or </body>
                for tag in (b'</head>', b'</body>'):
                    if tag in content:
                        response.content = content.replace(tag, self._CSRF_JS + tag, 1)
                        if 'Content-Length' in response:
                            response['Content-Length'] = len(response.content)
                        break

        return response
