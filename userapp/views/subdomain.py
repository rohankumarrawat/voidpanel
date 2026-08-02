"""
VoidApp API — Subdomain management endpoints.

GET    /api/v1/subdomains/       — List subdomains
POST   /api/v1/subdomains/create/ — Create subdomain
POST   /api/v1/subdomains/delete/ — Delete subdomain
"""

import os
import sys
import logging

from control.models import (
    subdomainname, domain as Domain, user as CtrlUser, package as Package
)
from userapp.decorators import (
    api_response, api_auth_required, parse_json_body, require_post
)

logger = logging.getLogger('voidpanel.userapp')


@api_auth_required()
def api_subdomain_list(request):
    """List all subdomains for the current user's domain."""
    ctrl_user = request.ctrl_user
    subs = subdomainname.objects.filter(domain=ctrl_user.domain)

    sub_list = []
    for s in subs:
        sub_list.append({
            'id': s.id,
            'subdomain': s.subdomain,
            'name': s.name,
            'domain': s.domain,
            'ssl_active': getattr(s, 'sslstatus', False),
        })

    pkg = _get_pkg(ctrl_user.hosting_package)
    total = _safe_int(pkg.subdomain) if pkg else 0

    return api_response(data={
        'subdomains': sub_list,
        'used': len(sub_list),
        'total': total,
        'unlimited': total == 0,
    })


@api_auth_required()
@require_post
def api_subdomain_create(request):
    """
    Create a new subdomain.

    POST body: { "name": "blog" }
    Creates blog.example.com for the user's domain.
    """
    data = parse_json_body(request)
    name = data.get('name', '').strip().lower()
    ctrl_user = request.ctrl_user
    domain_name = ctrl_user.domain

    if not name:
        return api_response(error='Subdomain name is required.', status=400)

    import re
    if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', name):
        return api_response(error='Invalid subdomain name.', status=400)

    full = f'{name}.{domain_name}'

    # Check if exists
    if subdomainname.objects.filter(subdomain=full).exists():
        return api_response(error='Subdomain already exists.', status=409)

    # Check quota
    pkg = _get_pkg(ctrl_user.hosting_package)
    if pkg:
        max_sub = _safe_int(pkg.subdomain)
        if max_sub > 0:
            current = subdomainname.objects.filter(domain=domain_name).count()
            if current >= max_sub:
                return api_response(
                    error=f'Quota exceeded. Maximum {max_sub} subdomains allowed.',
                    status=403
                )

    try:
        from voidplatform.config import paths
        from function import run_command

        dom_obj = Domain.objects.get(domain=domain_name)
        oldpath = os.path.join(paths.HOME_BASE, dom_obj.dir)
        path = os.path.join(oldpath, 'public_html', name)

        # Create directory
        if sys.platform != 'win32':
            run_command(f'sudo mkdir -p {path}')
        else:
            os.makedirs(path, exist_ok=True)

        # Create default index
        try:
            from function import create_default_index_html
            create_default_index_html(path, full)
        except Exception:
            pass

        # Set ownership
        if sys.platform != 'win32':
            from panel.views import get_web_user
            run_command(f'sudo chown -R {dom_obj.dir}:{get_web_user()} {path}')
            run_command(f'sudo chmod -R 750 {path}')

        # Create web server config
        if sys.platform != 'win32':
            from voidplatform.linux.web import get_active_engine, get_active_engine_manager
            engine = get_active_engine()
            mgr = get_active_engine_manager()

            if engine == 'nginx':
                file_path = os.path.join(paths.NGINX_SITES_AVAILABLE, f'{full}.conf')
                try:
                    from panel.views import generate_ssl_certificates, create_nginx_ssl_conf
                    cert_path, key_path = generate_ssl_certificates(full, oldpath + '/ssl', oldpath + '/logs')
                    if cert_path and key_path:
                        create_nginx_ssl_conf(file_path, full, path, cert_path, key_path)
                    else:
                        # HTTP-only fallback
                        fallback = f"server {{\n    listen 80;\n    server_name {full};\n    root {path};\n    index index.php index.html;\n    location / {{\n        try_files $uri $uri/ =404;\n    }}\n    location ~ \\.php$ {{\n        include snippets/fastcgi-php.conf;\n        fastcgi_pass unix:/run/php/php8.3-fpm.sock;\n    }}\n}}\n"
                        with open(file_path, 'w') as f:
                            f.write(fallback)
                except Exception:
                    pass

                # Symlink & test
                run_command(f'sudo ln -sf {paths.NGINX_SITES_AVAILABLE}/{full}.conf {paths.NGINX_SITES_ENABLED}/')
                test_res = mgr.test_config()
                if not test_res.success:
                    _rm = os.path.join(paths.NGINX_SITES_ENABLED, f'{full}.conf')
                    if os.path.exists(_rm):
                        os.remove(_rm)
                    return api_response(error='Web server config test failed. Reverted.', status=500)
            else:
                # OpenLiteSpeed
                result = mgr.create_site(full, path, php_version='8.3', unix_user=dom_obj.dir)
                if not result.success:
                    return api_response(error=f'Web server config failed: {result.error}', status=500)

            # Add DNS record
            try:
                from panel.views import create_bind_recordsforsubdomain, get_dns_service_name
                from voidplatform import get_platform
                zone_file = os.path.join(paths.BIND_ZONE_DIR, f'db.{domain_name}')
                create_bind_recordsforsubdomain(name, zone_file)
                get_platform().services.reload(get_dns_service_name())
            except Exception:
                pass

        # Save to database
        sub_obj = subdomainname.objects.create(subdomain=full, name=name, domain=domain_name)

        # Cloudflare sync
        try:
            from panel.views import sync_cloudflare_subdomain_add
            sync_cloudflare_subdomain_add(domain_name, full)
        except Exception:
            pass

        try:
            from control.activity import log_activity
            log_activity(request, 'success', 'domain', domain=domain_name,
                         action=f'Subdomain created: {full}',
                         detail='Created via VoidApp API')
        except Exception:
            pass

        return api_response(data={
            'id': sub_obj.id,
            'subdomain': full,
            'message': 'Subdomain created successfully.'
        })

    except Exception as e:
        logger.exception('Failed to create subdomain %s', full)
        return api_response(error=f'Failed to create subdomain: {str(e)}', status=500)


@api_auth_required()
@require_post
def api_subdomain_delete(request):
    """
    Delete a subdomain.

    POST body: { "subdomain": "blog.example.com" }
    """
    data = parse_json_body(request)
    subdomain_full = data.get('subdomain', '').strip().lower()
    ctrl_user = request.ctrl_user

    if not subdomain_full:
        return api_response(error='Subdomain is required.', status=400)

    # Ownership check
    try:
        sub_obj = subdomainname.objects.get(subdomain=subdomain_full, domain=ctrl_user.domain)
    except subdomainname.DoesNotExist:
        return api_response(error='Subdomain not found.', status=404)

    try:
        from voidplatform.config import paths
        import shutil

        dom_obj = Domain.objects.get(domain=ctrl_user.domain)
        path = os.path.join(paths.HOME_BASE, dom_obj.dir, 'public_html', sub_obj.name)

        # Remove directory
        try:
            shutil.rmtree(path)
        except Exception:
            pass

        # Remove web config
        if sys.platform != 'win32':
            from voidplatform.linux.web import get_active_engine_manager
            mgr = get_active_engine_manager()
            mgr.delete_site(subdomain_full)

        # Cloudflare sync
        try:
            from panel.views import sync_cloudflare_subdomain_delete
            sync_cloudflare_subdomain_delete(ctrl_user.domain, subdomain_full)
        except Exception:
            pass

    except Exception as e:
        logger.warning('Partial cleanup for subdomain %s: %s', subdomain_full, e)

    sub_obj.delete()

    try:
        from control.activity import log_activity
        log_activity(request, 'success', 'domain', domain=ctrl_user.domain,
                     action=f'Subdomain deleted: {subdomain_full}',
                     detail='Deleted via VoidApp API')
    except Exception:
        pass

    return api_response(data={'message': f'Subdomain {subdomain_full} deleted.'})


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_pkg(name):
    try:
        return Package.objects.get(name=name) if name else None
    except Package.DoesNotExist:
        return None

def _safe_int(val):
    try:
        v = str(val).strip().lower()
        if v in ('unlimited', '∞', ''):
            return 0
        return int(v)
    except (ValueError, TypeError):
        return 0
