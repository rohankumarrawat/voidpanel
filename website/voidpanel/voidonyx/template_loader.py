"""
VoidOnyx Domain-Aware Template Loader
======================================
This loader intercepts template resolution and serves templates from
templates/voidonyx/ when the request comes from voidonyx.com/voidonyx.in,
and from templates/ when the request comes from voidpanel.com or localhost.

How it works:
- SiteMiddleware sets thread-local site_id on every request
- This loader checks site_id and prepends voidonyx templates dir when needed
- VoidPanel.com always sees templates/ (its own templates)
- VoidOnyx.com always sees templates/voidonyx/ FIRST (overrides), then templates/ (fallback)
"""

import threading
import os
from pathlib import Path
from django.template.loaders.filesystem import Loader as FileSystemLoader
from django.conf import settings

# Thread-local storage to hold the current request's site_id
_thread_locals = threading.local()


def set_current_site(site_id: str):
    """Called by SiteMiddleware to set the active site for this thread."""
    _thread_locals.site_id = site_id


def get_current_site() -> str:
    return getattr(_thread_locals, 'site_id', 'voidpanel')


class SiteTemplateLoader(FileSystemLoader):
    """
    A filesystem-based template loader that prepends the VoidOnyx templates dir
    ONLY when the current request comes from voidonyx.com / voidonyx.in.
    VoidPanel.com requests only see the default templates/ dir.
    """

    def get_dirs(self):
        site_id = get_current_site()
        base_dir = Path(settings.BASE_DIR)
        default_dir = base_dir / 'templates'
        voidonyx_dir = base_dir / 'templates' / 'voidonyx'

        if site_id == 'voidonyx' and voidonyx_dir.exists():
            # VoidOnyx: check voidonyx/ templates FIRST, fallback to main templates/
            return [str(voidonyx_dir), str(default_dir)]
        else:
            # VoidPanel or unknown: only use main templates/
            return [str(default_dir)]

