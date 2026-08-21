#!/usr/bin/env python3
"""Add csrf_failure_view to views.py"""
VIEWS_PATH = '/home/voidonyx/voidonyx/voidpanel/views.py'

stub = '''

def csrf_failure_view(request, reason=""):
    from django.http import HttpResponseForbidden
    return HttpResponseForbidden(
        '<h1>403 Forbidden</h1><p>CSRF verification failed. Request aborted.</p>',
        content_type='text/html',
    )
'''

with open(VIEWS_PATH, 'a') as f:
    f.write(stub)

# Verify
with open(VIEWS_PATH, 'r') as f:
    content = f.read()

if 'def csrf_failure_view' in content:
    print('CSRF_VIEW_ADDED_OK')
else:
    print('CSRF_VIEW_ADD_FAILED')
