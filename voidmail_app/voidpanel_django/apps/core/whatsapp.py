import html
import json
import logging
import re
import urllib.request
import urllib.error
from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_PHONE_NUMBER_ID = "1236644629538328"
DEFAULT_META_API_URL = f"https://graph.facebook.com/v21.0/{DEFAULT_PHONE_NUMBER_ID}/messages"
DEFAULT_OTP_TEMPLATE = "otp_template"
DEFAULT_ALERT_TEMPLATE = "email_alert_template"


def clean_whatsapp_phone(phone_number: str) -> str:
    """
    Cleans phone number to strictly digits in international E.164 without leading '+'.
    - Indian 10-digit numbers (e.g. 9354519271) become 919354519271.
    - Numbers with leading '0' or '00' are normalized to proper country prefix.
    """
    clean = re.sub(r'[^0-9]', '', str(phone_number or '').strip())
    # Strip double zero international prefix
    if clean.startswith("00"):
        clean = clean[2:]
    if len(clean) == 10:
        clean = "91" + clean
    elif clean.startswith("0") and len(clean) == 11:
        clean = "91" + clean[1:]
    return clean


def sanitize_meta_param(val: str, max_len: int = 120, default: str = "-") -> str:
    """
    Sanitizes text parameters for Meta WhatsApp Cloud API:
    - Unescapes HTML entities (&amp; -> &)
    - Strips raw HTML tags (<br>, <b>, etc.)
    - Removes newlines, tabs, and carriage returns (Meta strictly forbids newlines in body params)
    - Collapses consecutive whitespace to a single space
    - Truncates to max_len safely without breaking words if possible
    - Guarantees non-empty text (Meta rejects empty params with HTTP 400)
    """
    if not val:
        return default
    text = html.unescape(str(val))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r'\s{2,}', ' ', text).strip()
    if not text:
        return default
    if len(text) > max_len:
        text = text[:max_len - 3].rstrip() + "..."
    return text


def format_sender_display(sender_raw: str, from_email: str = None) -> str:
    """
    Beautifies email sender format into an executive display string:
    - "Sundar Pichai <sundar@google.com>" -> "Sundar Pichai (sundar@google.com)"
    - "support@gov.in" -> "support@gov.in"
    """
    raw = str(sender_raw or '').strip()
    match = re.match(r'^([^<]+)<([^>]+)>$', raw)
    if match:
        name = match.group(1).strip().strip('"\'')
        email = match.group(2).strip()
        if name and email and name.lower() != email.lower():
            return f"{name} ({email})"
        return email or name
    if from_email and from_email.strip() and from_email.strip().lower() != raw.lower():
        return f"{raw} ({from_email.strip()})"
    return raw or "VIP Contact"


def get_whatsapp_settings():
    """Retrieves current SystemSetting configuration for WhatsApp"""
    try:
        from apps.mail_engine.models import SystemSetting
        setting = SystemSetting.objects.first()
        return setting
    except Exception as e:
        logger.error(f"Failed to load SystemSetting: {e}")
        return None


def execute_meta_http_request(api_url: str, api_key: str, payload: dict) -> tuple[bool, dict]:
    """Internal HTTP dispatcher with timeout and detailed error decoding"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "VoidOnyx-MetaWhatsAppGateway/2.0"
    }
    try:
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=req_data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            return True, res_json
    except urllib.error.HTTPError as http_err:
        err_body = http_err.read().decode('utf-8')
        logger.error(f"Meta WhatsApp API HTTP {http_err.code}: {err_body}")
        try:
            err_json = json.loads(err_body)
            return False, err_json
        except Exception:
            return False, {"error": f"HTTP {http_err.code}: {err_body}"}
    except Exception as e:
        logger.error(f"Meta WhatsApp API Request Exception: {e}")
        return False, {"error": str(e)}


def send_meta_whatsapp_otp(phone_number: str, otp_code: str, setting=None) -> tuple[bool, dict]:
    """
    Sends an OTP verification code via Meta WhatsApp Cloud API using the active 'otp_template'.
    Includes intelligent component fallbacks (Copy Code Button -> Body Only) and language fallbacks (en -> en_US).
    """
    clean_phone = clean_whatsapp_phone(phone_number)
    if not clean_phone or len(clean_phone) < 10:
        return False, {"error": f"Invalid phone number format: '{phone_number}'"}

    if setting is None:
        setting = get_whatsapp_settings()

    api_url = (setting.whatsapp_api_url if setting and setting.whatsapp_api_url else DEFAULT_META_API_URL).strip()
    api_key = (setting.whatsapp_api_key if setting and setting.whatsapp_api_key else '').strip()
    template_name = (setting.whatsapp_template if setting and setting.whatsapp_template else DEFAULT_OTP_TEMPLATE).strip()

    if not api_key:
        return False, {"error": "WhatsApp Access Token (API Key) is not configured in Super Admin settings"}

    code_str = str(otp_code).strip()

    # Attempt 1: Standard Meta Authentication Template with Body + Copy Code / URL Button
    payload_with_button = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": code_str}]
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": code_str}]
                }
            ]
        }
    }

    ok, res = execute_meta_http_request(api_url, api_key, payload_with_button)
    if ok:
        logger.info(f"WhatsApp OTP delivered to {clean_phone} via button template: {res}")
        return True, res

    err_code = res.get("error", {}).get("code") if isinstance(res, dict) else None
    err_msg = str(res.get("error", {}).get("message", ""))

    # Attempt 2: If button component failed (e.g. template has no button or different index), retry with body only
    if err_code in (100, 132000) or "button" in err_msg.lower() or "component" in err_msg.lower():
        logger.info(f"Retrying OTP for {clean_phone} with body-only component...")
        payload_body_only = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": code_str}]
                    }
                ]
            }
        }
        ok2, res2 = execute_meta_http_request(api_url, api_key, payload_body_only)
        if ok2:
            return True, res2

    # Attempt 3: If language 'en' failed with 132001 (template not found), try 'en_US'
    if err_code == 132001 or "template" in err_msg.lower():
        logger.info(f"Retrying OTP for {clean_phone} with language en_US...")
        payload_en_us = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "en_US"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": code_str}]
                    }
                ]
            }
        }
        ok3, res3 = execute_meta_http_request(api_url, api_key, payload_en_us)
        if ok3:
            return True, res3

    return False, res


def send_meta_whatsapp_email_alert(
    phone_number: str,
    sender: str,
    subject: str,
    date_str: str,
    snippet: str,
    rule_label: str = None,
    setting=None
) -> tuple[bool, dict]:
    """
    Sends an executive incoming email alert notification via WhatsApp.
    - Uses approved Meta Cloud API template ('email_alert_template') with 4 sanitized parameters.
    - Falls back to a visually formatted rich WhatsApp text message on custom REST gateways.
    """
    clean_phone = clean_whatsapp_phone(phone_number)
    if not clean_phone or len(clean_phone) < 10:
        return False, {"error": f"Invalid phone number format: '{phone_number}'"}

    if setting is None:
        setting = get_whatsapp_settings()

    api_url = (setting.whatsapp_api_url if setting and setting.whatsapp_api_url else DEFAULT_META_API_URL).strip()
    api_key = (setting.whatsapp_api_key if setting and setting.whatsapp_api_key else '').strip()
    alert_template = getattr(setting, 'whatsapp_alert_template', DEFAULT_ALERT_TEMPLATE) or DEFAULT_ALERT_TEMPLATE

    # Beautify and sanitize parameters for Meta Template Variable rules
    v_sender = sanitize_meta_param(format_sender_display(sender), max_len=60, default="VIP Contact")
    v_subject = sanitize_meta_param(subject, max_len=80, default="(No Subject)")
    v_time = sanitize_meta_param(date_str, max_len=30, default="Just now")
    v_preview = sanitize_meta_param(snippet, max_len=140, default="(Encrypted message content)")

    is_meta_api = "graph.facebook.com" in api_url

    if is_meta_api:
        if not api_key:
            return False, {"error": "WhatsApp Access Token is not configured in Super Admin"}

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "template",
            "template": {
                "name": alert_template.strip(),
                "language": {"code": "en"},
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": v_sender},
                            {"type": "text", "text": v_subject},
                            {"type": "text", "text": v_time},
                            {"type": "text", "text": v_preview}
                        ]
                    }
                ]
            }
        }

        ok, res = execute_meta_http_request(api_url, api_key, payload)
        if ok:
            logger.info(f"WhatsApp Email Alert delivered to {clean_phone}: {res}")
            return True, res

        err_code = res.get("error", {}).get("code") if isinstance(res, dict) else None
        err_msg = str(res.get("error", {}).get("message", ""))

        # If language 'en' failed, try 'en_US'
        if err_code == 132001 or "template" in err_msg.lower():
            logger.info(f"Retrying Email Alert for {clean_phone} with language en_US...")
            payload["template"]["language"]["code"] = "en_US"
            ok2, res2 = execute_meta_http_request(api_url, api_key, payload)
            if ok2:
                return True, res2

        # Provide a crystal clear diagnostic if the template is not yet approved in Meta Business Suite
        if err_code == 132001:
            friendly_err = (
                f"Meta WhatsApp Template '{alert_template}' was not found in your Meta Business Suite. "
                f"Please create an approved UTILITY template named '{alert_template}' with 4 variables: "
                f"{{1}}=Sender, {{2}}=Subject, {{3}}=Time, {{4}}=Preview, or update the template name in Super Admin."
            )
            return False, {"error": friendly_err, "meta_details": res}

        return False, res

    else:
        # Visually stunning ASCII/Markdown layout for Generic REST WhatsApp Gateways
        tag_line = f"🏷️ *Rule:* {rule_label}\n" if rule_label else ""
        formatted_msg = (
            f"📬 *VoidOnyx VIP Email Alert*\n"
            f"────────────────────────\n"
            f"👤 *From:* {v_sender}\n"
            f"📌 *Subject:* {v_subject}\n"
            f"⏰ *Time:* {v_time}\n"
            f"{tag_line}"
            f"\n"
            f"📝 *Message Preview:*\n"
            f"_{v_preview}_\n"
            f"────────────────────────\n"
            f"🌐 *Open Webmail:* https://mail.voidonyx.in\n"
            f"🛡️ _Protected by VoidOnyx Sovereign Shield_"
        )

        payload = {
            "to": clean_phone,
            "phone": clean_phone,
            "message": formatted_msg,
            "text": formatted_msg,
            "body": formatted_msg,
            "sender_id": getattr(setting, 'whatsapp_sender_id', '') or '+91 93541 61484'
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "VoidOnyx-Mailing-Gateway/2.0"
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(api_url, data=req_data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=12) as response:
                res_body = response.read().decode('utf-8')
                try:
                    res_json = json.loads(res_body)
                except Exception:
                    res_json = {"response": res_body}
                return True, res_json
        except Exception as e:
            return False, {"error": str(e)}

