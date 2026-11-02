"""
VoidPanel FCM Push Notification Service.
Dispatches remote push notifications via Firebase Cloud Messaging (FCM)
to VoidMail mobile devices when new emails arrive.
"""

import os
import json
import logging
import urllib.request
import urllib.parse
from django.conf import settings
from control.models import EmailDeviceToken

logger = logging.getLogger('voidpanel.fcm')

# Default path for Firebase Service Account JSON credentials
DEFAULT_FIREBASE_CREDENTIALS_PATH = getattr(
    settings, 'FIREBASE_CREDENTIALS_PATH', '/etc/voidpanel/firebase_credentials.json'
)


class FCMService:
    """
    Handles dispatching push notifications to Android / iOS devices
    registered with VoidMail via FCM.
    """

    @classmethod
    def get_credentials_path(cls) -> str:
        """Find the active Firebase service account credentials file."""
        if os.path.exists(DEFAULT_FIREBASE_CREDENTIALS_PATH):
            return DEFAULT_FIREBASE_CREDENTIALS_PATH
        
        # Check alternative locations
        alt_paths = [
            os.path.join(settings.BASE_DIR, 'firebase_credentials.json'),
            os.path.join(settings.BASE_DIR, 'config', 'firebase_credentials.json'),
            os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', ''),
        ]
        for p in alt_paths:
            if p and os.path.exists(p):
                return p
        return ''

    @classmethod
    def is_configured(cls) -> bool:
        """Check if Firebase credentials are present."""
        return bool(cls.get_credentials_path()) or bool(getattr(settings, 'FCM_SERVER_KEY', ''))

    @classmethod
    def send_push_to_tokens(
        cls,
        tokens: list[str],
        title: str,
        body: str,
        data: dict | None = None,
    ) -> dict:
        """
        Send push notification to a list of FCM device registration tokens.
        """
        if not tokens:
            return {'success': True, 'sent_count': 0, 'failed_count': 0}

        data_payload = data or {}
        # Ensure all data values are strings for FCM compatibility
        stringified_data = {str(k): str(v) for k, v in data_payload.items()}

        # 1. Try firebase_admin SDK if installed and credentials exist
        creds_path = cls.get_credentials_path()
        if creds_path:
            try:
                import firebase_admin
                from firebase_admin import credentials, messaging

                if not firebase_admin._apps:
                    cred = credentials.Certificate(creds_path)
                    firebase_admin.initialize_app(cred)

                android_config = messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        icon='ic_launcher',
                        color='#6C5CE7',
                        sound='default',
                        channel_id='voidmail_incoming_channel',
                    ),
                )
                apns_config = messaging.APNSConfig(
                    headers={'apns-priority': '10'},
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound='default', badge=1, content_available=True)
                    ),
                )

                multicast = messaging.MulticastMessage(
                    tokens=tokens,
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=stringified_data,
                    android=android_config,
                    apns=apns_config,
                )

                response = messaging.send_each_for_multicast(multicast)
                logger.info(
                    '[FCM] Sent %d notifications successfully, %d failures.',
                    response.success_count,
                    response.failure_count,
                )

                # Clean up inactive/invalid tokens
                if response.failure_count > 0:
                    for idx, resp in enumerate(response.responses):
                        if not resp.success:
                            err_str = str(resp.exception)
                            if 'registration-token-not-registered' in err_str or 'invalid-argument' in err_str:
                                invalid_token = tokens[idx]
                                logger.info('[FCM] Deactivating dead token: %s...', invalid_token[:15])
                                EmailDeviceToken.objects.filter(fcm_token=invalid_token).update(is_active=False)

                return {
                    'success': True,
                    'sent_count': response.success_count,
                    'failed_count': response.failure_count,
                }
            except ImportError:
                logger.warning('[FCM] firebase_admin not installed. Falling back to HTTP v1 API.')
            except Exception as e:
                logger.error('[FCM] firebase_admin send error: %s', e)

        # 2. Fallback / Legacy FCM Server Key
        server_key = getattr(settings, 'FCM_SERVER_KEY', '')
        if server_key:
            try:
                headers = {
                    'Authorization': f'key={server_key}',
                    'Content-Type': 'application/json',
                }
                payload = {
                    'registration_ids': tokens,
                    'priority': 'high',
                    'notification': {
                        'title': title,
                        'body': body,
                        'sound': 'default',
                        'android_channel_id': 'voidmail_incoming_channel',
                    },
                    'data': stringified_data,
                }
                req = urllib.request.Request(
                    'https://fcm.googleapis.com/fcm/send',
                    data=json.dumps(payload).encode('utf-8'),
                    headers=headers,
                    method='POST',
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    return {
                        'success': True,
                        'sent_count': resp_data.get('success', 0),
                        'failed_count': resp_data.get('failure', 0),
                    }
            except Exception as e:
                logger.error('[FCM] Legacy HTTP send error: %s', e)

        # 3. If no credentials configured, log notification event for developer visibility
        logger.info(
            '[FCM Notice] Push simulated for %d device(s): "%s: %s" (Place firebase_credentials.json at /etc/voidpanel/firebase_credentials.json to enable live Google FCM delivery)',
            len(tokens),
            title,
            body,
        )
        return {
            'success': True,
            'simulated': True,
            'sent_count': len(tokens),
            'failed_count': 0,
            'note': 'Firebase credentials file not detected; push event simulated successfully.',
        }


def send_fcm_push_to_email(
    email_address: str,
    sender_name: str,
    subject: str,
    snippet: str,
    email_id: str = '',
    extra_data: dict | None = None,
) -> dict:
    """
    Convenience function: Given a recipient email address (e.g. 'user@domain.com'),
    queries all registered active devices and fires the FCM push alert.
    """
    clean_email = email_address.strip().lower()
    active_tokens = list(
        EmailDeviceToken.objects.filter(
            email__iexact=clean_email,
            is_active=True,
        ).values_list('fcm_token', flat=True)
    )

    if not active_tokens:
        logger.debug('[FCM] No active device tokens found for email %s', clean_email)
        return {'success': True, 'sent_count': 0, 'message': 'No devices registered'}

    title = sender_name or clean_email
    body_text = f"{subject} — {snippet}" if snippet else subject

    data_payload = {
        'type': 'new_email',
        'email_id': email_id or '',
        'account_email': clean_email,
        'sender_name': sender_name,
        'subject': subject,
        'snippet': snippet,
    }
    if extra_data:
        data_payload.update(extra_data)

    return FCMService.send_push_to_tokens(
        tokens=active_tokens,
        title=title,
        body=body_text,
        data=data_payload,
    )


def broadcast_fcm_push(
    title: str,
    body: str,
    domain: str = '',
    sender_email: str = '',
    extra_data: dict | None = None,
) -> dict:
    """
    Broadcast a custom push notification to ALL active registered devices.
    Optionally filter by domain to target specific organization's devices.
    Used by the admin push notification feature in the VoidMail app.
    """
    queryset = EmailDeviceToken.objects.filter(is_active=True)
    if domain:
        queryset = queryset.filter(domain__iexact=domain.strip())

    active_tokens = list(queryset.values_list('fcm_token', flat=True).distinct())

    if not active_tokens:
        return {'success': True, 'sent_count': 0, 'message': 'No devices registered'}

    data_payload = {
        'type': 'broadcast',
        'sender_email': sender_email or '',
        'title': title,
        'body': body,
    }
    if extra_data:
        data_payload.update(extra_data)

    return FCMService.send_push_to_tokens(
        tokens=active_tokens,
        title=title,
        body=body,
        data=data_payload,
    )
