"""
control/license.py — VoidPanel License Utility

Handles local license state and communication with voidpanel.com's
license API endpoints.  The validate response now returns the full
tier + feature-flag payload, which is cached locally so the panel
never needs to call voidpanel.com on every page request.
"""
import json
import secrets
import socket
import logging
import datetime

import requests
from django.utils import timezone

log = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
VOIDPANEL_LICENSE_API = "https://voidpanel.com"
_REGISTER_URL  = f"{VOIDPANEL_LICENSE_API}/api/license/register/"
_VALIDATE_URL  = f"{VOIDPANEL_LICENSE_API}/api/license/validate/"
_REQUEST_TIMEOUT = 12  # seconds

# ── Tier → full feature set map ───────────────────────────────────────────────
_TIER_FEATURES = {
    'starter': {
        'marketing_suite': True, 'seo_tools': True, 'social_suite': True,
        'whatsapp': False, 'docker': False, 'script_installer': False,
        'ai_assistant': False, 'digital_suite': False, 'reseller': False,
        'white_label': False, 'priority_support': False,
    },
    'pro': {
        'marketing_suite': True, 'seo_tools': True, 'social_suite': True,
        'whatsapp': True, 'docker': False, 'script_installer': False,
        'ai_assistant': False, 'digital_suite': False, 'reseller': False,
        'white_label': False, 'priority_support': False,
    },
    'advanced': {
        'marketing_suite': True, 'seo_tools': True, 'social_suite': True,
        'whatsapp': True, 'docker': True, 'script_installer': True,
        'ai_assistant': True, 'digital_suite': True, 'reseller': True,
        'white_label': False, 'priority_support': False,
    },
    'unlimited': {
        'marketing_suite': True, 'seo_tools': True, 'social_suite': True,
        'whatsapp': True, 'docker': True, 'script_installer': True,
        'ai_assistant': True, 'digital_suite': True, 'reseller': True,
        'white_label': True, 'priority_support': True,
    },
}


def _get_override_tier():
    """Return VOID_TIER_OVERRIDE from settings if set, else None."""
    try:
        from django.conf import settings
        return getattr(settings, 'VOID_TIER_OVERRIDE', None)
    except Exception:
        return None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_hostname():
    try:
        return socket.getfqdn()
    except Exception:
        return "unknown"


def _update_license_from_response(lic, data: dict):
    """
    Apply the tier / features / expiry fields returned by api/license/validate
    onto the local PanelLicense object and save.
    """
    update_fields = ['status', 'last_checked']

    new_status = data.get("status", "invalid")
    lic.status = new_status
    lic.last_checked = timezone.now()

    # Tier & features
    if "tier" in data:
        lic.tier = data["tier"]
        update_fields.append("tier")
    if "features" in data:
        lic.features_json = data["features"]
        update_fields.append("features_json")
    if "is_trial" in data:
        lic.is_trial = data["is_trial"]
        update_fields.append("is_trial")
    if "expires_at" in data and data["expires_at"]:
        from django.utils.dateparse import parse_datetime
        exp = parse_datetime(data["expires_at"])
        if exp:
            lic.expires_at = exp
            update_fields.append("expires_at")

    lic.save(update_fields=update_fields)
    return lic


# ── Public API ────────────────────────────────────────────────────────────────

def get_license():
    """Return the stored PanelLicense singleton, or None if not yet activated."""
    from control.models import PanelLicense
    return PanelLicense.objects.first()


def is_licensed():
    """
    Return True if a valid, non-suspended license exists locally.
    This is called on EVERY request by LicenseMiddleware — must be fast.
    """
    lic = get_license()
    return lic is not None and lic.status == "active"


def get_features() -> dict:
    """
    Return the feature-flag dict for this installation.
    If VOID_TIER_OVERRIDE is set in settings.py, returns the full feature set
    for that tier regardless of what voidpanel.com says.
    Falls back to an empty dict (everything disabled) if no license found.
    """
    override = _get_override_tier()
    if override and override in _TIER_FEATURES:
        return dict(_TIER_FEATURES[override])
    lic = get_license()
    if lic is None:
        return {}
    # If tier is set locally and features_json is empty, synthesise from tier map
    if lic.features_json:
        return lic.features_json
    return dict(_TIER_FEATURES.get(lic.tier, _TIER_FEATURES['starter']))


def has_feature(key: str, default: bool = False) -> bool:
    """Quick helper to check a single feature flag."""
    return bool(get_features().get(key, default))


def get_tier() -> str:
    """Return the current license tier slug ('starter', 'pro', 'advanced', 'unlimited')."""
    override = _get_override_tier()
    if override:
        return override
    lic = get_license()
    return lic.tier if lic else 'starter'


def register_and_activate(email: str, password: str, mode: str = 'login') -> dict:
    """
    POST to voidpanel.com to register (or log in) and receive a license key.
    Stores the returned key locally with tier + features.

    Args:
        mode: 'login' to authenticate an existing account,
              'register' to create a new voidpanel.com account first.

    Returns dict:
        {"ok": True, "key": "...", "tier": "...", "is_trial": bool} on success
        {"ok": False, "error": "..."} on failure
    """
    from control.models import PanelLicense

    payload = {
        "email":    email,
        "password": password,
        "hostname": _get_hostname(),
        "mode":     mode,
    }
    try:
        resp = requests.post(_REGISTER_URL, json=payload, timeout=_REQUEST_TIMEOUT)
        data = resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "error": f"Could not reach voidpanel.com: {exc}"}
    except ValueError:
        return {"ok": False, "error": "Invalid response from voidpanel.com"}

    if not data.get("key"):
        return {"ok": False, "error": data.get("error", "License server returned no key.")}

    # Store / update the local license record
    expires_at = None
    if data.get("expires_at"):
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(data["expires_at"])

    PanelLicense.objects.all().delete()  # enforce singleton
    lic = PanelLicense.objects.create(
        key           = data["key"],
        email         = email,
        status        = "active",
        hostname      = _get_hostname(),
        tier          = data.get("tier", "starter"),
        is_trial      = data.get("is_trial", False),
        expires_at    = expires_at,
        features_json = data.get("features", {}),
        issued_at     = timezone.now(),
        last_checked  = timezone.now(),
    )
    log.info("VoidPanel license activated: %s tier=%s trial=%s", data["key"][:16], lic.tier, lic.is_trial)
    return {
        "ok":       True,
        "key":      data["key"],
        "tier":     lic.tier,
        "is_trial": lic.is_trial,
        "message":  data.get("trial_message", ""),
    }


def activate_with_key(key: str) -> dict:
    """
    Validate a manually pasted license key against voidpanel.com.
    If valid, stores it locally with tier + features.

    Returns dict:
        {"ok": True, "key": "...", "tier": "..."} on success
        {"ok": False, "error": "..."} on failure
    """
    from control.models import PanelLicense

    key = key.strip()
    if not key or len(key) < 32:
        return {"ok": False, "error": "License key is too short. Please paste the full key."}

    # First try validate endpoint (returns full features payload)
    try:
        resp = requests.post(_VALIDATE_URL, json={"key": key, "hostname": _get_hostname()}, timeout=_REQUEST_TIMEOUT)
        data = resp.json()
    except requests.RequestException as exc:
        return {"ok": False, "error": f"Could not reach voidpanel.com: {exc}"}
    except ValueError:
        return {"ok": False, "error": "Invalid response from voidpanel.com"}

    if data.get("status") not in ("active", "ok"):
        return {"ok": False, "error": data.get("error", "License key validation failed.")}

    expires_at = None
    if data.get("expires_at"):
        from django.utils.dateparse import parse_datetime
        expires_at = parse_datetime(data["expires_at"])

    # Store the confirmed key locally
    PanelLicense.objects.all().delete()  # enforce singleton
    lic = PanelLicense.objects.create(
        key           = key,
        email         = "",
        status        = "active",
        hostname      = _get_hostname(),
        tier          = data.get("tier", "starter"),
        is_trial      = data.get("is_trial", False),
        expires_at    = expires_at,
        features_json = data.get("features", {}),
        issued_at     = timezone.now(),
        last_checked  = timezone.now(),
    )
    log.info("VoidPanel license activated via key: %s tier=%s", key[:16], lic.tier)
    return {"ok": True, "key": key, "tier": lic.tier}


def refresh_license() -> bool:
    """
    Called nightly by Celery Beat. Re-validates the stored key against
    voidpanel.com and updates local status + tier + features.

    If VOID_TIER_OVERRIDE is set in settings.py, skips the remote API call
    entirely and re-applies the override tier + feature set to the DB so the
    Celery task can never downgrade the installation back to Starter.

    Returns True if license is still valid after refresh.
    """
    from control.models import PanelLicense

    # ── Override path: skip remote call, re-pin override tier ────────────────
    override = _get_override_tier()
    if override and override in _TIER_FEATURES:
        lic = PanelLicense.objects.first()
        if lic:
            lic.tier          = override
            lic.features_json = dict(_TIER_FEATURES[override])
            lic.status        = 'active'
            lic.last_checked  = timezone.now()
            lic.save(update_fields=['tier', 'features_json', 'status', 'last_checked'])
            log.info("VoidPanel license refresh: VOID_TIER_OVERRIDE=%s — skipping remote call, tier pinned.", override)
        return True

    # ── Normal path: validate against voidpanel.com ───────────────────────────
    lic = PanelLicense.objects.first()
    if not lic:
        log.warning("VoidPanel license refresh: no local license found.")
        return False

    try:
        resp = requests.post(
            _VALIDATE_URL,
            json={"key": lic.key},
            timeout=_REQUEST_TIMEOUT,
        )
        data = resp.json()
    except requests.RequestException as exc:
        # Fail-open: keep current state if voidpanel.com is unreachable
        log.warning("VoidPanel license refresh failed (network): %s. Keeping current status.", exc)
        lic.last_checked = timezone.now()
        lic.save(update_fields=["last_checked"])
        return lic.status == "active"
    except ValueError:
        log.warning("VoidPanel license refresh: invalid JSON response.")
        return lic.status == "active"

    _update_license_from_response(lic, data)

    log.info("VoidPanel license refreshed — status: %s tier: %s", lic.status, lic.tier)
    return lic.status == "active"

