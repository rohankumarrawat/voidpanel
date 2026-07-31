import os, sys, django
sys.path.append("/home/voidonyx/voidonyx")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voidpanel.settings")
django.setup()

from voidpanel.ai_api import _call_huggingface, _call_gemini, _call_openai, _call_claude, AiProviderConfig

c = AiProviderConfig.get()
print("Active Provider:", c.active_provider)
print("Key:", c.get_active_key())
print("Model:", c.get_active_model())

provider = c.active_provider
key = c.get_active_key()
model = c.get_active_model()

try:
    if provider == 'huggingface':
        res = _call_huggingface(key, model, "You are a helpful assistant.", [], "Hello, testing AI connection.")
    elif provider == 'gemini':
        res = _call_gemini(key, model, "You are a helpful assistant.", [], "Hello, testing AI connection.")
    elif provider == 'openai':
        res = _call_openai(key, model, "You are a helpful assistant.", [], "Hello, testing AI connection.")
    elif provider == 'claude':
        res = _call_claude(key, model, "You are a helpful assistant.", [], "Hello, testing AI connection.")
    print("SUCCESS RESPONSE:", res)
except Exception as e:
    print("AI ERROR:", str(e))
