import json
import re
import secrets
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from .models import BurnOnReadMessage, VoidMaskAlias, VaultItem

def strip_spy_pixels(html_content):
    """
    Strips hidden 1x1 tracking pixels and beacon <img> tags from newsletters
    """
    # Regex to match 0 or 1px width/height images
    pattern = r'<img[^>]*(width=["\']?[01]["\']?|height=["\']?[01]["\']?|style=["\'][^"\']*(width:\s*[01]px|height:\s*[01]px)[^"\']*)[^>]*>'
    cleaned_html = re.sub(pattern, '<!-- [VoidShield: Spy Tracking Pixel Stripped] -->', html_content, flags=re.IGNORECASE)
    return cleaned_html

@csrf_exempt
def create_burn_message(request):
    """Create a self-destructing message"""
    if request.method == 'POST':
        data = json.loads(request.body)
        payload = data.get('content', '')
        msg = BurnOnReadMessage.objects.create(encrypted_payload=payload)
        return JsonResponse({
            'success': True,
            'token': msg.secret_token,
            'url': f'https://voidonyx.in/secret/{msg.secret_token}'
        })
    return JsonResponse({'error': 'POST required'}, status=400)

def view_burn_message(request, token):
    """View and immediately self-destruct the message"""
    msg = get_object_or_404(BurnOnReadMessage, secret_token=token)
    if msg.is_burned:
        return JsonResponse({'status': 'burned', 'message': '🔥 This secret message has self-destructed and no longer exists.'})
    
    # Reveal and immediately burn
    content = msg.encrypted_payload
    msg.is_burned = True
    msg.view_count += 1
    msg.encrypted_payload = '[DESTROYED]'
    msg.save()
    
    return JsonResponse({'status': 'revealed', 'content': content, 'burned': True})

@csrf_exempt
def generate_voidmask_alias(request):
    """Generate a disposable email alias"""
    if request.method == 'POST':
        data = json.loads(request.body)
        real_email = data.get('real_email', 'rohan@voidonyx.com')
        label = data.get('label', 'Shopping')
        
        alias_prefix = f"mask.{secrets.token_hex(4)}"
        alias_email = f"{alias_prefix}@voidonyx.in"
        
        alias = VoidMaskAlias.objects.create(
            alias_email=alias_email,
            real_destination=real_email,
            label=label
        )
        return JsonResponse({
            'success': True,
            'alias_email': alias.alias_email,
            'real_destination': alias.real_destination
        })
    return JsonResponse({'error': 'POST required'}, status=400)
