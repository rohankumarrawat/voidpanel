"""
Central AI Gateway for VoidPanel.
Receives context + chat history from installed panels, routes to the active
AI provider (Gemini / Claude / OpenAI) configured in the super admin portal,
and streams back the response or tool-call cards.

API keys are read from the AiProviderConfig database table — NOT from env vars
or settings.py. Super admin configures them at /super-admin/ai-keys/.
"""

import json
import re
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from data.models import AiProviderConfig, PanelLicenseRecord, CustomerProfile, ChipTransaction


# ── Helpers ───────────────────────────────────────────────────────────────────
def _cors_response(data, status=200):
    """Return a JsonResponse that allows cross-origin requests from any panel."""
    resp = JsonResponse(data, status=status)
    resp['Access-Control-Allow-Origin'] = '*'
    resp['Access-Control-Allow-Headers'] = 'Content-Type, X-Panel-Host, X-License-Key'
    resp['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
    return resp


def _build_system_prompt(system_prompt, context, tools):
    context_str = json.dumps(context, indent=2)
    return f"""{system_prompt}

# LIVE SERVER CONTEXT (auto-gathered from the panel right now):
```json
{context_str}
```

# HOW TO USE TOOLS:
When you need to run a command on the server, output ONLY the following JSON block (no other text):
```json
{{
  "tool_calls": [
    {{
      "name": "run_terminal_command",
      "arguments": {{"command": "exact_bash_command_here"}}
    }}
  ]
}}
```

AVAILABLE TOOLS:
{json.dumps(tools, indent=2)}

RULES:
- If diagnosing a problem, ALWAYS start by reading the relevant log first.
- NEVER run destructive commands (rm -rf, format, wipe, etc.) without asking.
- If you don't need a tool, respond with helpful plain text only.
- You know the full VoidPanel architecture. Use exact paths and commands.
"""


def _call_gemini(api_key, model, system_instruction, history, user_msg):
    """Route request to Google Gemini REST API with 429 retry."""
    import time as _time
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    contents = []
    for msg in history:
        role = 'user' if msg.get('role') == 'user' else 'model'
        contents.append({'role': role, 'parts': [{'text': msg.get('content', '')}]})
    contents.append({'role': 'user', 'parts': [{'text': user_msg}]})

    payload = {
        'system_instruction': {'parts': [{'text': system_instruction}]},
        'contents': contents,
        'generationConfig': {'temperature': 0.15, 'maxOutputTokens': 2048},
    }

    for attempt in range(2):          # try twice: initial + one retry after pause
        resp = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']
        if resp.status_code == 429:
            if attempt == 0:
                _time.sleep(3)        # wait 3 s then retry once
                continue
            raise Exception(
                "⚠️ Gemini API rate limit reached (429). Your free-tier quota is exhausted.\n\n"
                "To fix this:\n"
                "1. Go to https://aistudio.google.com → enable billing on your project, OR\n"
                "2. Generate a new Gemini API key and update it at voidpanel.com/super-admin/ai-keys/, OR\n"
                "3. Switch to the 'gemini-1.5-flash' model (higher free quota) in the AI Keys settings."
            )
        raise Exception(f"Gemini API error {resp.status_code}: {resp.text[:300]}")



def _call_claude(api_key, model, system_instruction, history, user_msg):
    """Route request to Anthropic Claude Messages API."""
    url = "https://api.anthropic.com/v1/messages"

    messages = []
    for msg in history:
        role = 'user' if msg.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': msg.get('content', '')})
    messages.append({'role': 'user', 'content': user_msg})

    payload = {
        'model': model,
        'max_tokens': 2048,
        'system': system_instruction,
        'messages': messages,
    }
    headers = {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=45)
    if resp.status_code != 200:
        raise Exception(f"Claude API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data['content'][0]['text']


def _call_openai(api_key, model, system_instruction, history, user_msg):
    """Route request to OpenAI Chat Completions API."""
    url = "https://api.openai.com/v1/chat/completions"

    messages = [{'role': 'system', 'content': system_instruction}]
    for msg in history:
        role = 'user' if msg.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': msg.get('content', '')})
    messages.append({'role': 'user', 'content': user_msg})

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': 2048,
        'temperature': 0.15,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=45)
    if resp.status_code != 200:
        raise Exception(f"OpenAI API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data['choices'][0]['message']['content']


def _call_huggingface(api_key, model, system_instruction, history, user_msg):
    """Route request to Hugging Face Inference API."""
    url = "https://router.huggingface.co/v1/chat/completions"


    messages = [{'role': 'system', 'content': system_instruction}]
    for msg in history:
        role = 'user' if msg.get('role') == 'user' else 'assistant'
        messages.append({'role': role, 'content': msg.get('content', '')})
    messages.append({'role': 'user', 'content': user_msg})

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': 2048,
        'temperature': 0.15,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=45)
    if resp.status_code != 200:
        raise Exception(f"Hugging Face API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return data['choices'][0]['message']['content']


def _extract_tool_calls(ai_text):
    """Parse JSON tool-call block from AI response if present."""
    match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', ai_text)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(1))
        if 'tool_calls' not in parsed or not isinstance(parsed['tool_calls'], list):
            return None
        formatted = []
        for call in parsed['tool_calls']:
            formatted.append({
                'function': {
                    'name': call.get('name', 'run_terminal_command'),
                    'arguments': json.dumps(call.get('arguments', {}))
                }
            })
        return formatted
    except (json.JSONDecodeError, KeyError):
        return None


# ── Main View ─────────────────────────────────────────────────────────────────
@csrf_exempt
def api_ai_chat(request):
    """
    POST /api/ai/chat/
    Called by installed VoidPanel instances via panel/ai_views.py
    """
    if request.method == 'OPTIONS':
        return _cors_response({})

    if request.method != 'POST':
        return _cors_response({'status': 'error', 'message': 'Only POST allowed'}, 405)

    try:
        data = json.loads(request.body)
    except Exception as e:
        return _cors_response({'status': 'error', 'message': f'Invalid JSON: {e}'}, 400)

    # ── Verify license key and deduct chips ──
    license_key = request.headers.get('X-License-Key', '').strip()
    if not license_key:
        license_key = data.get('license_key', '').strip()
        if not license_key:
            panel_host = request.headers.get('X-Panel-Host', '').strip()
            if panel_host:
                record = PanelLicenseRecord.objects.filter(server_ip__icontains=panel_host).first()
                if record:
                    license_key = record.key

    if not license_key:
        return _cors_response({'status': 'error', 'message': 'Missing license key'}, 400)

    try:
        record = PanelLicenseRecord.objects.get(key=license_key)
    except PanelLicenseRecord.DoesNotExist:
        return _cors_response({'status': 'error', 'message': 'Invalid license key'}, 403)

    if record.status != PanelLicenseRecord.STATUS_ACTIVE:
        return _cors_response({'status': 'error', 'message': f'License is {record.status}'}, 403)

    try:
        profile = record.user.customer_profile
    except Exception:
        profile, _ = CustomerProfile.objects.get_or_create(user=record.user)

    chips_cost = 5  # Deduct 5 chips per query/request
    if profile.balance_chips < chips_cost:
        return _cors_response({'status': 'error', 'message': 'Credit limit expired. Please recharge your chips.'}, 402)

    profile.balance_chips = max(0, profile.balance_chips - chips_cost)
    profile.save(update_fields=['balance_chips'])

    ChipTransaction.objects.create(
        user=record.user,
        amount=-chips_cost,
        transaction_type='adjustment',
        description='Agentic AI request'
    )

    try:
        # ── 1. Load config from database ──
        config = AiProviderConfig.get()

        if not config.is_configured:
            return _cors_response({
                'status': 'error',
                'message': (
                    f'No API key configured for the active provider ({config.get_active_provider_display()}). '
                    'Super admin must add the API key at: voidpanel.com/super-admin/ai-keys/'
                )
            }, 503)

        api_key  = config.get_active_key()
        model    = config.get_active_model()
        provider = config.active_provider

        # ── 2. Extract payload from panel ──
        system_prompt = data.get('system_prompt', '')
        context       = data.get('server_context', {})
        tools         = data.get('tools', [])
        history       = data.get('history', [])
        user_msg      = data.get('message', '')

        if not user_msg:
            return _cors_response({'status': 'error', 'message': 'message field is required'}, 400)

        full_system = _build_system_prompt(system_prompt, context, tools)

        # ── 3. Route to active provider ──
        if provider == 'gemini':
            ai_text = _call_gemini(api_key, model, full_system, history, user_msg)
        elif provider == 'claude':
            ai_text = _call_claude(api_key, model, full_system, history, user_msg)
        elif provider == 'openai':
            ai_text = _call_openai(api_key, model, full_system, history, user_msg)
        elif provider == 'huggingface':
            ai_text = _call_huggingface(api_key, model, full_system, history, user_msg)
        else:
            return _cors_response({'status': 'error', 'message': f'Unknown provider: {provider}'}, 500)

        # ── 4. Check for tool calls in response ──
        tool_calls = _extract_tool_calls(ai_text)
        if tool_calls:
            return _cors_response({
                'status': 'success',
                'response': 'I need to run a command to help you with this. Please review and approve:',
                'tool_calls': tool_calls,
            })

        # ── 5. Normal text response ──
        # Token deduction hook (enable when billing is wired up):
        # panel_host = request.headers.get('X-Panel-Host', '')
        # license = PanelLicenseRecord.objects.filter(server_ip__icontains=panel_host).first()
        # if license:
        #     license.ai_tokens = max(0, license.ai_tokens - config.tokens_per_request)
        #     license.save(update_fields=['ai_tokens'])

        return _cors_response({
            'status': 'success',
            'response': ai_text,
            'tool_calls': [],
        })

    except requests.exceptions.Timeout:
        return _cors_response({'status': 'error', 'message': 'The AI provider timed out. Please try again.'}, 504)
    except Exception as e:
        return _cors_response({'status': 'error', 'message': str(e)}, 500)
