import base64
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import EmailTrackingLog, FollowUpSequence, TextSnippet, SharedThread

# 1x1 transparent GIF
TRANSPARENT_PIXEL_GIF = base64.b64decode(
    b'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
)

def track_pixel_view(request, token):
    """Zero-Plugin Tracking Pixel endpoint (returns 1x1 transparent GIF)"""
    try:
        log = EmailTrackingLog.objects.get(token=token)
        log.open_count += 1
        now = timezone.now()
        if not log.first_opened_at:
            log.first_opened_at = now
        log.last_opened_at = now
        log.last_ip_address = request.META.get('REMOTE_ADDR', '')
        log.last_user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        log.save()
    except EmailTrackingLog.DoesNotExist:
        pass
    
    response = HttpResponse(TRANSPARENT_PIXEL_GIF, content_type='image/gif')
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response

def track_link_redirect(request, token):
    """Link click tracking proxy"""
    target_url = request.GET.get('url', 'https://voidonyx.in')
    try:
        log = EmailTrackingLog.objects.get(token=token)
        log.open_count += 1
        log.last_opened_at = timezone.now()
        log.save()
    except EmailTrackingLog.DoesNotExist:
        pass
    return redirect(target_url)

def view_shared_thread(request, token):
    """View shareable email thread online"""
    thread = get_object_or_404(SharedThread, thread_token=token)
    return render(request, 'sales_tools/shared_thread.html', {'thread': thread})

@csrf_exempt
def snippets_api(request):
    """API to fetch user snippets for fast auto-expansion"""
    snippets = list(TextSnippet.objects.values('shortcut', 'title', 'content'))
    return JsonResponse({'snippets': snippets})
