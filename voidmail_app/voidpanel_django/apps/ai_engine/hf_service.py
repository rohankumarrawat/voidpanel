import urllib.request, json, ssl
from django.utils import timezone
from .models import HuggingFaceApiKey

ROUTER_URL = 'https://router.huggingface.co/v1/chat/completions'

DEFAULT_KEYS = [
    ('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', 'rohanunsung@gmail.com', 'meta-llama/Llama-3.1-8B-Instruct'),
    ('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', 'rkrawatfreak@gmail.com', 'meta-llama/Llama-3.1-8B-Instruct')
]

def ensure_default_keys():
    """Ensure user's provided Hugging Face keys exist in the database"""
    for key, label, model in DEFAULT_KEYS:
        HuggingFaceApiKey.objects.get_or_create(
            api_key=key,
            defaults={'label': label, 'model_name': model, 'is_active': True}
        )

def call_huggingface_with_failover(messages, max_tokens=400, temperature=0.7):
    """
    Executes a chat completion call against Hugging Face.
    Cycles through active keys. If a key hits 429, 401, quota limit, or error,
    it automatically fails over to the next key in the pool!
    """
    ensure_default_keys()
    keys = list(HuggingFaceApiKey.objects.filter(is_active=True).order_by('error_count', 'id'))
    if not keys:
        return {'success': False, 'error': 'No active Hugging Face API keys configured.'}

    ctx = ssl._create_unverified_context()
    last_err = None

    for key_obj in keys:
        payload = json.dumps({
            'model': key_obj.model_name or 'meta-llama/Llama-3.1-8B-Instruct',
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature
        }).encode('utf-8')

        req = urllib.request.Request(
            ROUTER_URL,
            data=payload,
            headers={
                'Authorization': f'Bearer {key_obj.api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'VoidOnyx-AI/1.0'
            }
        )

        try:
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                content = result['choices'][0]['message']['content'].strip()
                # Update usage stats
                key_obj.usage_count += 1
                key_obj.last_used = timezone.now()
                key_obj.save(update_fields=['usage_count', 'last_used'])
                return {
                    'success': True,
                    'content': content,
                    'key_label': key_obj.label,
                    'model': key_obj.model_name
                }
        except Exception as e:
            err_msg = str(e)
            if hasattr(e, 'read'):
                try:
                    err_msg += " " + e.read().decode('utf-8')[:200]
                except Exception:
                    pass
            key_obj.error_count += 1
            key_obj.last_error = err_msg[:500]
            key_obj.save(update_fields=['error_count', 'last_error'])
            last_err = err_msg
            continue  # Failover to next key in rotation!

    return {
        'success': False,
        'error': f'All Hugging Face API keys exhausted or rate-limited: {last_err}'
    }
