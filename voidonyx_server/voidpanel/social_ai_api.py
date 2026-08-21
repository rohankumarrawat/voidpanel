"""
VoidOnyx Social AI API Gateway
─────────────────────────────
Processes AI requests from VoidPanel Social Studio instances.
Deducts chips from the user's VoidOnyx CustomerProfile and
routes to the configured AI provider (text) or HuggingFace (images).

Endpoints:
  POST /api/social-ai/generate/   → ai_social_generate
  GET  /api/social-ai/balance/    → ai_social_balance
  GET  /api/social-ai/config/     → ai_social_config
"""

import json
import logging
import requests as http_requests
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _identify_user(request):
    """
    Identify the VoidOnyx user from the request.
    Priority: X-VoidOnyx-User header → authenticated Django user → None
    Returns (user_obj, error_response).
    """
    username = request.headers.get('X-VoidOnyx-User', '').strip()

    if username:
        try:
            return User.objects.get(username=username), None
        except User.DoesNotExist:
            # Try by email
            try:
                return User.objects.get(email=username), None
            except (User.DoesNotExist, User.MultipleObjectsReturned):
                return None, JsonResponse({'error': 'User not found', 'code': 'user_not_found'}, status=404)

    if request.user.is_authenticated:
        return request.user, None

    return None, JsonResponse({'error': 'Authentication required', 'code': 'auth_required'}, status=401)


def _get_chip_balance(user):
    """Get the user's chip balance from CustomerProfile."""
    from data.models import CustomerProfile
    try:
        profile = user.customer_profile
        return profile.balance_chips
    except CustomerProfile.DoesNotExist:
        # Create profile with 0 balance
        profile = CustomerProfile.objects.create(user=user, balance_chips=0)
        return 0


def _deduct_chips(user, amount, request_type, prompt_summary=''):
    """
    Deduct chips from the user's CustomerProfile.
    Returns (success: bool, balance_after: int, error_msg: str).
    """
    from data.models import CustomerProfile, SocialAIChipTransaction

    try:
        profile = user.customer_profile
    except CustomerProfile.DoesNotExist:
        return False, 0, 'No billing profile found. Please contact support.'

    if profile.balance_chips < amount:
        return False, profile.balance_chips, f'Insufficient chips. Need {amount}, have {profile.balance_chips}.'

    profile.balance_chips -= amount
    profile.save(update_fields=['balance_chips'])

    # Log the transaction
    SocialAIChipTransaction.objects.create(
        user=user,
        request_type=request_type,
        chips_deducted=amount,
        balance_after=profile.balance_chips,
        prompt_summary=prompt_summary[:200],
    )

    return True, profile.balance_chips, ''


def _check_daily_limit(user, max_per_day):
    """Check if user has exceeded daily AI request limit."""
    if max_per_day <= 0:
        return True  # 0 = unlimited

    from data.models import SocialAIChipTransaction
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    count = SocialAIChipTransaction.objects.filter(
        user=user, created_at__gte=today_start
    ).count()
    return count < max_per_day


def _call_text_ai(prompt, provider_config):
    """
    Call the configured text AI provider.
    Returns the generated text or raises an exception.
    """
    provider = provider_config.active_provider
    api_key = provider_config.get_active_key()
    model = provider_config.get_active_model()

    if not api_key:
        raise ValueError(f'No API key configured for {provider}. Contact admin.')

    if provider == 'gemini':
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
        payload = {
            'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'maxOutputTokens': 1024, 'temperature': 0.8}
        }
        r = http_requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            data = r.json()
            candidates = data.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                return parts[0].get('text', '') if parts else ''
        raise ValueError(f'Gemini API error: {r.status_code} {r.text[:200]}')

    elif provider == 'openai':
        url = 'https://api.openai.com/v1/chat/completions'
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1024,
            'temperature': 0.8,
        }
        r = http_requests.post(url, json=payload, headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }, timeout=30)
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
        raise ValueError(f'OpenAI API error: {r.status_code} {r.text[:200]}')

    elif provider == 'claude':
        url = 'https://api.anthropic.com/v1/messages'
        payload = {
            'model': model,
            'max_tokens': 1024,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        r = http_requests.post(url, json=payload, headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }, timeout=30)
        if r.status_code == 200:
            data = r.json()
            content = data.get('content', [])
            return content[0].get('text', '') if content else ''
        raise ValueError(f'Claude API error: {r.status_code} {r.text[:200]}')

    elif provider == 'huggingface':
        # Use HF Router API (chat completions format) with fallback
        hf_endpoints = [
            'https://router.huggingface.co/v1/chat/completions',
            'https://router.huggingface.co/novita/v3/openai/chat/completions',
            'https://router.huggingface.co/together/v1/chat/completions',
        ]
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 1024,
            'temperature': 0.8,
        }
        hf_headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        }
        last_err = None
        for ep in hf_endpoints:
            try:
                r = http_requests.post(ep, json=payload, headers=hf_headers, timeout=45)
                if r.status_code == 200:
                    data = r.json()
                    return data['choices'][0]['message']['content']
                err_text = r.text[:300]
                if 'not supported' in err_text.lower() or r.status_code in (404, 422):
                    last_err = err_text
                    continue
                if r.status_code in (401, 403, 429):
                    raise ValueError(f'HuggingFace API error {r.status_code}: {err_text}')
                last_err = err_text
            except http_requests.exceptions.Timeout:
                last_err = 'Request timed out'
                continue
            except ValueError:
                raise
            except Exception as e:
                last_err = str(e)
                continue
        raise ValueError(
            f"HuggingFace: Model '{model}' not available. {last_err}. "
            f"Try 'Qwen/Qwen2.5-72B-Instruct' or 'meta-llama/Llama-3.1-8B-Instruct'."
        )

    raise ValueError(f'Unknown AI provider: {provider}')


def _call_image_ai(prompt, hf_api_key, hf_model):
    """
    Call HuggingFace Inference API for image generation.
    Returns base64 image data or raises an exception.
    """
    import base64

    if not hf_api_key:
        raise ValueError('No HuggingFace API key configured for image generation.')

    url = f'https://api-inference.huggingface.co/models/{hf_model}'
    payload = {'inputs': prompt}
    r = http_requests.post(url, json=payload, headers={
        'Authorization': f'Bearer {hf_api_key}'
    }, timeout=60)

    if r.status_code == 200:
        # HF returns raw image bytes
        content_type = r.headers.get('content-type', '')
        if 'image' in content_type:
            img_b64 = base64.b64encode(r.content).decode('utf-8')
            return f'data:{content_type};base64,{img_b64}'
        # JSON response (some models return URLs)
        try:
            data = r.json()
            if isinstance(data, list) and data:
                return data[0].get('url', data[0].get('generated_image', ''))
            return str(data)
        except Exception:
            img_b64 = base64.b64encode(r.content).decode('utf-8')
            return f'data:image/png;base64,{img_b64}'

    if r.status_code == 503:
        raise ValueError('Image model is loading. Please try again in 30 seconds.')

    raise ValueError(f'Image generation failed: HTTP {r.status_code}')


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
def api_social_ai_generate(request):
    """
    POST /api/social-ai/generate/
    Main AI generation endpoint. Handles text (captions, repurpose) and images.

    Body: {
        "type": "text" | "image",
        "prompt": "...",
        "platform": "instagram",   // optional, for text
        "tone": "professional",    // optional, for text
        "mode": "caption" | "repurpose" | "hashtags",  // optional
        "style": "realistic",      // optional, for images
    }

    Headers:
        X-VoidOnyx-User: username or email
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user, err = _identify_user(request)
    if err:
        return err

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    req_type = body.get('type', 'text')
    prompt = body.get('prompt', '').strip()
    platform = body.get('platform', 'general')
    tone = body.get('tone', 'professional')
    mode = body.get('mode', 'caption')
    style = body.get('style', '')

    if not prompt:
        return JsonResponse({'error': 'Prompt is required'}, status=400)

    # Load settings
    from data.models import SocialPlatformSettings, AiProviderConfig
    sps = SocialPlatformSettings.get()
    ai_cfg = AiProviderConfig.get()

    # Check feature enabled
    if req_type == 'text' and not sps.ai_text_enabled:
        return JsonResponse({'error': 'AI text generation is currently disabled.', 'code': 'feature_disabled'}, status=403)
    if req_type == 'image' and not sps.ai_image_enabled:
        return JsonResponse({'error': 'AI image generation is currently disabled.', 'code': 'feature_disabled'}, status=403)

    # Check daily limit
    if not _check_daily_limit(user, sps.ai_max_requests_per_day):
        return JsonResponse({
            'error': f'Daily limit of {sps.ai_max_requests_per_day} AI requests reached. Try again tomorrow.',
            'code': 'daily_limit'
        }, status=429)

    # Determine chip cost
    chip_cost = sps.ai_text_chips_cost if req_type == 'text' else sps.ai_image_chips_cost

    # Deduct chips
    success, balance_after, error_msg = _deduct_chips(user, chip_cost, req_type, prompt[:100])
    if not success:
        return JsonResponse({
            'error': error_msg,
            'code': 'insufficient_chips',
            'chips_remaining': balance_after,
            'chips_needed': chip_cost,
        }, status=402)

    # Generate content
    try:
        if req_type == 'text':
            # Build the enhanced prompt based on mode
            if mode == 'caption':
                full_prompt = (
                    f"Write 3 creative social media captions for a {platform} post about: {prompt}. "
                    f"Tone: {tone}. Include relevant hashtags. "
                    f"Format as a numbered list (1., 2., 3.). Each caption should be unique and engaging."
                )
            elif mode == 'repurpose':
                full_prompt = (
                    f"Repurpose the following content for {platform}. "
                    f"Tone: {tone}. Make it platform-native with appropriate length, style, and hashtags.\n\n"
                    f"Original content:\n{prompt}"
                )
            elif mode == 'hashtags':
                full_prompt = (
                    f"Generate 20 relevant trending hashtags for: {prompt}. "
                    f"Platform: {platform}. Include a mix of popular and niche hashtags. "
                    f"Format as a space-separated list starting with #."
                )
            elif mode == 'tone_adjust':
                full_prompt = (
                    f"Rewrite the following text in a {tone} tone for {platform}:\n\n{prompt}"
                )
            else:
                full_prompt = prompt

            result = _call_text_ai(full_prompt, ai_cfg)
            return JsonResponse({
                'status': 'success',
                'type': 'text',
                'result': result,
                'chips_deducted': chip_cost,
                'chips_remaining': balance_after,
            })

        elif req_type == 'image':
            # Build image prompt
            img_prompt = prompt
            if style:
                img_prompt = f"{prompt}, {style} style, high quality, detailed"

            # Get HF key — prefer social-specific key, fallback to global
            hf_key = sps.hf_image_api_key or ai_cfg.huggingface_api_key
            hf_model = sps.hf_image_model

            result = _call_image_ai(img_prompt, hf_key, hf_model)
            return JsonResponse({
                'status': 'success',
                'type': 'image',
                'result': result,
                'chips_deducted': chip_cost,
                'chips_remaining': balance_after,
            })

        else:
            return JsonResponse({'error': f'Unknown request type: {req_type}'}, status=400)

    except ValueError as e:
        # Refund chips on AI provider error
        from data.models import CustomerProfile
        try:
            profile = user.customer_profile
            profile.balance_chips += chip_cost
            profile.save(update_fields=['balance_chips'])
        except Exception:
            pass  # Best effort refund
        logger.error(f'Social AI error for {user.username}: {e}')
        return JsonResponse({
            'error': str(e),
            'code': 'ai_error',
            'chips_refunded': chip_cost,
            'chips_remaining': balance_after + chip_cost,
        }, status=502)

    except Exception as e:
        logger.error(f'Social AI unexpected error: {e}')
        return JsonResponse({'error': 'An unexpected error occurred.', 'code': 'internal_error'}, status=500)


@csrf_exempt
def api_social_ai_balance(request):
    """
    GET /api/social-ai/balance/
    Returns the user's current chip balance and daily usage stats.
    """
    user, err = _identify_user(request)
    if err:
        return err

    from data.models import SocialPlatformSettings, SocialAIChipTransaction
    sps = SocialPlatformSettings.get()

    balance = _get_chip_balance(user)

    # Today's usage
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_txns = SocialAIChipTransaction.objects.filter(user=user, created_at__gte=today_start)
    daily_used = today_txns.count()
    daily_chips_spent = sum(t.chips_deducted for t in today_txns)

    return JsonResponse({
        'chips_remaining': balance,
        'daily_used': daily_used,
        'daily_limit': sps.ai_max_requests_per_day,
        'daily_chips_spent': daily_chips_spent,
        'text_cost': sps.ai_text_chips_cost,
        'image_cost': sps.ai_image_chips_cost,
        'ai_text_enabled': sps.ai_text_enabled,
        'ai_image_enabled': sps.ai_image_enabled,
    })


@csrf_exempt
def api_social_ai_config(request):
    """
    GET /api/social-ai/config/
    Returns AI feature configuration for the frontend.
    """
    from data.models import SocialPlatformSettings
    sps = SocialPlatformSettings.get()
    return JsonResponse(sps.get_ai_config_dict())
