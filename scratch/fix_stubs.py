#!/usr/bin/env python3
"""Fix the broken stub functions at the end of views.py on the live server."""

VIEWS_PATH = '/home/voidonyx/voidonyx/voidpanel/views.py'

with open(VIEWS_PATH, 'r') as f:
    content = f.read()

# Remove everything after the last valid function (the broken stubs)
# Find the marker: the stubs start after the last line of the original file
# The broken stubs start with "\ndef robots_txt"
marker = "\ndef robots_txt(request):"
idx = content.rfind(marker)
if idx > 0:
    content = content[:idx]
    print(f"[OK] Removed broken stubs starting at position {idx}")

# Now append clean stubs
clean_stubs = '''

def robots_txt(request):
    from django.http import HttpResponse
    lines = [
        "User-agent: *",
        "Disallow: /portal/",
        "Disallow: /super-admin/",
        "Disallow: /admin/",
        "Disallow: /api/",
        "Allow: /",
    ]
    return HttpResponse("\\n".join(lines), content_type="text/plain")


def sitemap_xml(request):
    from django.http import HttpResponse
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://voidonyx.in/</loc></url>
  <url><loc>https://voidonyx.in/pricing/</loc></url>
  <url><loc>https://voidonyx.in/login/</loc></url>
  <url><loc>https://voidonyx.in/register/</loc></url>
</urlset>"""
    return HttpResponse(xml, content_type="application/xml")


def refund_policy(request):
    return render(request, 'refund_policy.html')


def portal_blog_edit(request, blog_id=None):
    return redirect('/portal/')


def portal_subscriptions(request):
    return redirect('/portal/')


from django.views.decorators.csrf import csrf_exempt as _csrf_exempt_stub


@_csrf_exempt_stub
def api_create_subscription(request):
    from django.http import JsonResponse
    return JsonResponse({"error": "not implemented"}, status=501)


@_csrf_exempt_stub
def api_cancel_subscription(request):
    from django.http import JsonResponse
    return JsonResponse({"error": "not implemented"}, status=501)


@_csrf_exempt_stub
def api_quote_coupon_validate(request):
    from django.http import JsonResponse
    return JsonResponse({"error": "not implemented"}, status=501)
'''

content += clean_stubs

with open(VIEWS_PATH, 'w') as f:
    f.write(content)

print("[OK] Clean stubs appended")
print("FIX_COMPLETE")
