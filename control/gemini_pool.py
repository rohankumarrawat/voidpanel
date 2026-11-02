"""
VoidPanel Gemini Multi-Key Pool Manager
--------------------------------------
Provides thread-safe Round-Robin load balancing across multiple Google Gemini API keys,
with automatic interception of HTTP 429 Rate Limits / Quota Exceeded and seamless failover.
"""

import time
import json
import logging
import requests
from datetime import datetime, timezone as dt_timezone, timedelta
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiPoolManager:
    """
    Manages circular round-robin rotation and rate-limit failovers across configured Gemini API keys.
    """

    @classmethod
    def get_all_keys(cls):
        from control.models import GeminiAPIKey
        return GeminiAPIKey.objects.all()

    @classmethod
    def get_next_key(cls, exclude_ids=None):
        """
        Returns the next available Gemini API key using Round-Robin (Least Recently Used),
        filtering out inactive keys and keys currently in rate-limit cooldown.
        """
        from control.models import GeminiAPIKey
        exclude_ids = exclude_ids or []
        now = timezone.now()

        # Query active keys not in current exclusion list
        candidates = list(GeminiAPIKey.objects.filter(is_active=True).exclude(id__in=exclude_ids))

        if not candidates:
            # Check if any keys exist at all
            if not GeminiAPIKey.objects.filter(is_active=True).exists():
                raise RuntimeError(
                    "No active Gemini API keys found. Please add at least one Gemini API key in Super Admin."
                )
            raise RuntimeError("All active Gemini API keys have been attempted for this request.")

        # Filter out keys in active cooldown
        usable = [k for k in candidates if not k.cooldown_until or k.cooldown_until <= now]

        if not usable:
            # If all are in cooldown, pick the key whose cooldown expires soonest
            candidates.sort(key=lambda k: k.cooldown_until or now)
            selected = candidates[0]
            wait_seconds = max(1, int((selected.cooldown_until - now).total_seconds())) if selected.cooldown_until else 1
            logger.warning(f"All Gemini keys in cooldown. Earliest key {selected.label or selected.id} recovers in {wait_seconds}s.")
            return selected

        # Sort by least recently used (Circular Round-Robin)
        usable.sort(key=lambda k: k.last_used_at or datetime.min.replace(tzinfo=dt_timezone.utc))
        selected = usable[0]

        # Update usage timestamp and counts
        try:
            with transaction.atomic():
                selected.last_used_at = now
                selected.total_request_count += 1
                selected.daily_request_count += 1
                selected.save(update_fields=['last_used_at', 'total_request_count', 'daily_request_count'])
        except Exception as e:
            logger.warning(f"Could not update key usage metrics: {e}")

        return selected

    @classmethod
    def mark_rate_limited(cls, key_obj, cooldown_seconds=60):
        """Places a key in cooldown for cooldown_seconds after a 429 response."""
        try:
            with transaction.atomic():
                key_obj.rate_limit_hits += 1
                key_obj.cooldown_until = timezone.now() + timedelta(seconds=cooldown_seconds)
                key_obj.save(update_fields=['rate_limit_hits', 'cooldown_until'])
            logger.warning(
                f"Gemini key '{key_obj.label or key_obj.id}' marked in cooldown for {cooldown_seconds}s (Total 429s: {key_obj.rate_limit_hits})."
            )
        except Exception as e:
            logger.error(f"Error marking key rate limited: {e}")

    @classmethod
    def mark_invalid(cls, key_obj, reason="API Key Invalid"):
        """Disables an invalid or revoked key."""
        try:
            with transaction.atomic():
                key_obj.is_active = False
                key_obj.save(update_fields=['is_active'])
            logger.error(f"Gemini key '{key_obj.label or key_obj.id}' disabled permanently: {reason}")
        except Exception as e:
            logger.error(f"Error disabling key: {e}")

    @classmethod
    def test_key(cls, key_str, model_name="gemini-2.5-flash"):
        """
        Sends a test ping to Google Gemini API to verify validity and measure latency.
        Returns: (success: bool, message: str, latency_ms: int)
        """
        start_time = time.time()
        url = f"{GEMINI_API_BASE}/{model_name}:generateContent?key={key_str.strip()}"
        payload = {
            "contents": [{"parts": [{"text": "Reply with 'OK'"}]}],
            "generationConfig": {"maxOutputTokens": 10}
        }
        headers = {"Content-Type": "application/json"}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=12)
            latency_ms = int((time.time() - start_time) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                text = ""
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except (KeyError, IndexError):
                    pass
                return True, f"Connected successfully ({model_name}) - latency: {latency_ms}ms", latency_ms

            if resp.status_code == 429:
                return False, f"Rate limited / Quota exceeded (HTTP 429): {resp.text[:150]}", latency_ms

            if resp.status_code in (400, 403):
                return False, f"Invalid API Key or permission denied (HTTP {resp.status_code}): {resp.text[:150]}", latency_ms

            return False, f"Unexpected response (HTTP {resp.status_code}): {resp.text[:150]}", latency_ms

        except requests.exceptions.Timeout:
            return False, "Connection timed out after 12 seconds", 12000
        except Exception as e:
            return False, f"Connection error: {str(e)}", 0

    @classmethod
    def generate_content(cls, prompt, system_instruction=None, temperature=0.7, max_retries=5):
        """
        Executes a Gemini content generation request with Round-Robin key rotation and
        automatic failover if a key hits rate limit (429) or fails.
        """
        attempted_ids = []
        last_error = None

        for attempt in range(max_retries):
            try:
                key_obj = cls.get_next_key(exclude_ids=attempted_ids)
            except RuntimeError as e:
                raise RuntimeError(f"Key pool exhausted: {e}")

            attempted_ids.append(key_obj.id)
            model = key_obj.model_name or "gemini-2.5-flash"
            url = f"{GEMINI_API_BASE}/{model}:generateContent?key={key_obj.key}"

            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 8192,
                }
            }
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            headers = {"Content-Type": "application/json"}

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=60)

                # 1. Success
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "parts" in candidates[0].get("content", {}):
                        raw_text = candidates[0]["content"]["parts"][0]["text"]
                        return raw_text.strip()
                    raise RuntimeError("Gemini returned response without candidate content parts")

                # 2. Rate limit (429) or RESOURCE_EXHAUSTED
                if resp.status_code == 429 or "RESOURCE_EXHAUSTED" in resp.text:
                    cls.mark_rate_limited(key_obj, cooldown_seconds=60)
                    last_error = f"Key '{key_obj.label or key_obj.id}' rate-limited (HTTP 429). Retrying next key..."
                    logger.warning(last_error)
                    continue

                # 3. Invalid key or disabled billing
                if resp.status_code in (400, 403) and ("API_KEY_INVALID" in resp.text or "PERMISSION_DENIED" in resp.text):
                    cls.mark_invalid(key_obj, reason=resp.text[:120])
                    last_error = f"Key '{key_obj.label or key_obj.id}' rejected (HTTP {resp.status_code}). Retrying next key..."
                    logger.warning(last_error)
                    continue

                # 4. Model not available for this key (404) -> auto-switch to alternate model immediately
                if resp.status_code == 404:
                    alt_model = "gemini-3.8-flash" if "gemini-2.5" in model else "gemini-2.5-flash"
                    logger.warning(f"Model {model} returned 404 for key {key_obj.id}. Retrying with alternate model {alt_model}...")
                    alt_url = f"{GEMINI_API_BASE}/{alt_model}:generateContent?key={key_obj.key}"
                    try:
                        alt_resp = requests.post(alt_url, headers=headers, json=payload, timeout=60)
                        if alt_resp.status_code == 200:
                            key_obj.model_name = alt_model
                            key_obj.save(update_fields=['model_name'])
                            data = alt_resp.json()
                            candidates = data.get("candidates", [])
                            if candidates and "parts" in candidates[0].get("content", {}):
                                return candidates[0]["content"]["parts"][0]["text"].strip()
                    except Exception as e_alt:
                        logger.warning(f"Alternate model retry also failed for key {key_obj.id}: {e_alt}")

                # 5. Other HTTP errors
                resp.raise_for_status()

            except (requests.exceptions.RequestException, RuntimeError) as e:
                err_str = str(e).lower()
                if "429" in err_str or "resource_exhausted" in err_str:
                    cls.mark_rate_limited(key_obj, cooldown_seconds=60)
                    last_error = f"Key '{key_obj.label or key_obj.id}' rate-limited ({e}). Retrying..."
                    continue
                last_error = e
                logger.error(f"Gemini API request error with key {key_obj.id}: {e}")
                time.sleep(1)

        raise RuntimeError(f"Failed to generate after trying {len(attempted_ids)} Gemini API keys: {last_error}")
