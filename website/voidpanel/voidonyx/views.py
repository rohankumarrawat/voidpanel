"""
VoidOnyx views.py
==================
VoidOnyx shares ALL views with the voidpanel app — the domain-aware
template loader (voidonyx.template_loader.SiteTemplateLoader) automatically
serves templates from templates/voidonyx/ when request comes from voidonyx.com.

No view duplication is needed. This file exists for any VoidOnyx-specific
overrides or additions that aren't available in the voidpanel app.
"""

# All views are inherited from voidpanel.views via the shared URL conf.
# The SiteTemplateLoader switches template directories per domain.

# Example of a VoidOnyx-only view (if needed in the future):
# from django.shortcuts import render
# def voidonyx_index(request):
#     return render(request, 'index.html')  # Will serve templates/voidonyx/index.html when on voidonyx.com
