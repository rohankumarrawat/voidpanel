"""
VoidPanel Maildir Push Notification Monitor.
Extracts email metadata from newly delivered Maildir files and dispatches
FCM remote push notifications to registered VoidMail mobile apps.
"""

import os
import glob
import email
from email import policy
from email.parser import BytesParser
import logging
from django.conf import settings
from control.fcm_service import send_fcm_push_to_email

logger = logging.getLogger('voidpanel.fcm')


def parse_mail_file(file_path: str) -> dict:
    """
    Parse an RFC 822 email file from Maildir/new/ and return metadata.
    """
    try:
        with open(file_path, 'rb') as f:
            msg = BytesParser(policy=policy.default).parse(f)

        # Extract Subject
        subject = msg.get('Subject', '') or '(No Subject)'

        # Extract Sender
        sender_header = msg.get('From', '') or 'Unknown'
        sender_name = msg['From'].addresses[0].display_name if msg.get('From') and msg['From'].addresses else sender_header
        if not sender_name:
            sender_name = sender_header

        # Extract Recipient
        recipient = ''
        if msg.get('Delivered-To'):
            recipient = str(msg['Delivered-To']).strip()
        elif msg.get('To') and msg['To'].addresses:
            recipient = msg['To'].addresses[0].addr_spec
        elif msg.get('X-Original-To'):
            recipient = str(msg['X-Original-To']).strip()

        # Extract plain text snippet
        body_text = ''
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == 'text/plain':
                    try:
                        body_text = part.get_content()
                        break
                    except Exception:
                        pass
        else:
            try:
                body_text = msg.get_content()
            except Exception:
                pass

        snippet = ''
        if body_text:
            cleaned = ' '.join(body_text.split())
            snippet = cleaned[:120] + ('...' if len(cleaned) > 120 else '')

        return {
            'success': True,
            'subject': subject,
            'sender_name': sender_name,
            'recipient': recipient.lower(),
            'snippet': snippet,
            'message_id': msg.get('Message-ID', os.path.basename(file_path)),
        }
    except Exception as e:
        logger.error('Failed to parse mail file %s: %s', file_path, e)
        return {'success': False, 'error': str(e)}


def process_new_mail_file(file_path: str, fallback_recipient: str = '') -> dict:
    """
    Process a single newly delivered email file and trigger FCM push.
    """
    if not os.path.exists(file_path):
        return {'success': False, 'error': f'File not found: {file_path}'}

    info = parse_mail_file(file_path)
    if not info.get('success'):
        return info

    recipient = info.get('recipient') or fallback_recipient
    if not recipient:
        # Try inferring from path: .../<domain>/<user>/new/<filename>
        parts = file_path.replace('\\', '/').split('/')
        try:
            new_idx = parts.index('new')
            user_part = parts[new_idx - 1]
            domain_part = parts[new_idx - 2]
            if '@' in user_part:
                recipient = user_part
            elif '.' in domain_part:
                recipient = f"{user_part}@{domain_part}"
        except Exception:
            pass

    if not recipient:
        logger.warning('[FCM] Unable to determine recipient for mail file %s', file_path)
        return {'success': False, 'error': 'Recipient unknown'}

    # Trigger FCM Push
    result = send_fcm_push_to_email(
        email_address=recipient,
        sender_name=info.get('sender_name', 'New Message'),
        subject=info.get('subject', '(No Subject)'),
        snippet=info.get('snippet', ''),
        email_id=info.get('message_id', ''),
    )
    return result


def scan_and_notify_new_maildirs(base_dir: str = '/home') -> dict:
    """
    Scans all Maildir/new/ directories across domains/users and sends
    push notifications for any unprocessed emails.
    """
    search_patterns = [
        os.path.join(base_dir, '*', 'mail', '*', '*', 'new', '*'),
        os.path.join(base_dir, '*', 'Maildir', 'new', '*'),
        '/var/mail/vhosts/*/*/new/*',
    ]

    total_processed = 0
    for pattern in search_patterns:
        for mail_path in glob.glob(pattern):
            # Process new file
            res = process_new_mail_file(mail_path)
            if res.get('success'):
                total_processed += 1

    return {'success': True, 'processed_count': total_processed}
