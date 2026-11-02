import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from .models import LiveChatSession, LiveChatMessage


def _get_superuser_emails():
    """Return a list of all superuser email addresses."""
    return list(User.objects.filter(is_superuser=True).values_list('email', flat=True))


def _send_new_chat_notification(session):
    """Fire an HTML email to rohanfreakymg@gmail.com and contact@voidpanel.com when a new chat session opens."""
    user_display = session.user.email if session.user else f"{session.guest_name} ({session.guest_email})"
    user_type = "Registered Member ✅" if session.user else "Guest Visitor 👤"
    
    phone_display = session.guest_phone or "Not provided"
    if session.user and not session.guest_phone:
        try:
            phone_display = session.user.customer_profile.phone or "Not provided"
        except Exception:
            pass

    html_body = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:580px;margin:auto;background:#070d18;color:#e2eaf6;border-radius:14px;overflow:hidden;border:1px solid rgba(89,196,188,0.3);">
        <div style="background:linear-gradient(135deg,#59c4bc,#3de0d5);padding:24px 28px;">
            <h2 style="margin:0;color:#041a18;font-size:1.3rem;">💬 New Live Chat Request</h2>
            <p style="margin:6px 0 0;color:rgba(4,26,24,0.75);font-size:0.9rem;">Someone needs support on VoidOnyx / VoidPanel</p>
        </div>
        <div style="padding:28px;">
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;width:130px;">Session ID</td><td style="color:#59c4bc;font-weight:700;">#{session.id}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">User</td><td style="color:#e2eaf6;font-weight:600;">{user_display}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Phone / WhatsApp</td><td style="color:#38bdf8;font-weight:700;font-size:0.95rem;">{phone_display}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Type</td><td style="color:#e2eaf6;">{user_type}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Started</td><td style="color:#e2eaf6;">{session.created_at.strftime('%B %d, %Y at %H:%M UTC')}</td></tr>
            </table>
            <div style="margin-top:24px;text-align:center;">
                <a href="https://voidonyx.in/super-admin/livechat/{session.id}/" style="display:inline-block;padding:12px 28px;background:#59c4bc;color:#041a18;font-weight:700;border-radius:8px;text-decoration:none;font-size:0.9rem;">
                    🎯 Open Session &rarr;
                </a>
            </div>
        </div>
        <div style="background:rgba(255,255,255,0.03);padding:14px 28px;font-size:0.72rem;color:#4d637e;border-top:1px solid rgba(255,255,255,0.05);">
            VoidPanel Live Support System &bull; This is an automated notification.
        </div>
    </div>
    """

    from data.models import OutboundEmailProfile
    from django.core.mail.backends.smtp import EmailBackend
    
    try:
        smtp_profile = (
            OutboundEmailProfile.objects
            .filter(is_active=True, send_on_live_chat=True)
            .order_by('-is_default')
            .first()
        )
    except Exception:
        smtp_profile = None

    recipients = ['rohanfreakymg@gmail.com', 'contact@voidpanel.com']

    try:
        if smtp_profile:
            email = EmailMessage(
                subject=f'🔔 New Live Chat Request — Session #{session.id}',
                body=html_body,
                from_email=f'{smtp_profile.from_name or "VoidPanel Support"} <{smtp_profile.from_email}>',
                to=recipients,
                reply_to=[smtp_profile.reply_to_email] if smtp_profile.reply_to_email else [],
            )
            email.content_subtype = 'html'
            backend = EmailBackend(
                host=smtp_profile.smtp_host,
                port=smtp_profile.smtp_port,
                username=smtp_profile.smtp_username,
                password=smtp_profile.smtp_password,
                use_tls=smtp_profile.use_tls,
                use_ssl=smtp_profile.use_ssl,
                fail_silently=False,
            )
            backend.open()
            backend.send_messages([email])
            backend.close()
        else:
            email = EmailMessage(
                subject=f'🔔 New Live Chat Request — Session #{session.id}',
                body=html_body,
                from_email='VoidPanel Support <noreply@voidpanel.com>',
                to=recipients,
            )
            email.content_subtype = 'html'
            email.send(fail_silently=True)
    except Exception:
        pass


ADMIN_WHATSAPP_NUMBER = '919220953819'


def _send_whatsapp_template(to_phone, template_name, parameters, language='en'):
    """
    Send an approved Meta WhatsApp template message.
    Bypasses the 24-hour customer window and delivers 24/7.
    parameters: list of string values for {{1}}, {{2}}, etc.
    """
    import urllib.request
    import json
    import re as _re

    try:
        from data.models import WhatsAppConfig
        config = WhatsAppConfig.objects.filter(id=1).first()
    except Exception:
        config = None

    if not config or not config.api_phone_number_id or not config.api_access_token:
        return False, 'WhatsApp API credentials not configured'

    digits = _re.sub(r'[^\d]', '', to_phone)
    if len(digits) == 10:
        digits = '91' + digits

    api_ver = config.api_version or 'v20.0'
    url = f'https://graph.facebook.com/{api_ver}/{config.api_phone_number_id}/messages'

    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': digits,
        'type': 'template',
        'template': {
            'name': template_name,
            'language': {'code': language},
            'components': [
                {
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': str(p)} for p in parameters]
                }
            ]
        }
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        url, data=data, method='POST',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {config.api_access_token}',
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = json.loads(res.read().decode('utf-8'))
            if body.get('messages'):
                return True, ''
            return False, body.get('error', {}).get('message', 'Unknown API response')
    except urllib.error.HTTPError as exc:
        try:
            err_body = json.loads(exc.read().decode('utf-8'))
            err_msg = err_body.get('error', {}).get('message', str(exc))
        except Exception:
            err_msg = str(exc)
        return False, err_msg
    except Exception as exc:
        return False, str(exc)


def _send_chat_whatsapp_alert(session, event_type='new_chat'):
    """
    Send WhatsApp notification to admin (9220953819) via WhatsApp Business Cloud API.
    - 'new_chat': Sends approved Meta template 'admin_new_livechat_alert' (delivers 24/7).
    - 'no_agent': Sends approved Meta template 'live_chat_busy_followup' to customer.
    """
    from voidpanel.views import _send_whatsapp_message
    from data.models import WhatsAppLog

    if session.user:
        user_name = session.user.get_full_name() or session.user.username
        user_email = session.user.email or '(No email on file)'
        user_type = "Registered User ✅"
    else:
        user_name = session.guest_name or 'Guest'
        user_email = session.guest_email or '(No email provided)'
        user_type = "Guest Visitor 👤"

    phone = session.guest_phone or 'Not provided'

    if event_type == 'new_chat':
        # 1. Primary: Send approved Meta Template 'admin_new_livechat_alert' (delivers 24/7)
        # Parameters: {{1}}=Name, {{2}}=Email, {{3}}=Phone, {{4}}=Session ID
        ok, err = _send_whatsapp_template(
            ADMIN_WHATSAPP_NUMBER,
            'admin_new_livechat_alert',
            [user_name, user_email, phone, str(session.id)]
        )
        msg_logged = f"[Template: admin_new_livechat_alert] New Chat #{session.id} | {user_name} | {user_email} | {phone}"

        # 2. Fallback: Free-form text if template fails
        if not ok:
            admin_msg = (
                f"🔔 *New Live Chat Started!* 💬\n\n"
                f"A user has just opened a live chat support session:\n\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 *Name:* {user_name}\n"
                f"📧 *Email:* {user_email}\n"
                f"📱 *Phone:* {phone}\n"
                f"🏷️ *Account:* {user_type}\n"
                f"🆔 *Session ID:* #{session.id}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👉 *Join Chat Now:*\n"
                f"https://voidonyx.in/super-admin/livechat/{session.id}/\n\n"
                f"⏱️ _Please join within 2 minutes to assist the customer!_"
            )
            ok, err = _send_whatsapp_message(ADMIN_WHATSAPP_NUMBER, admin_msg)
            msg_logged = admin_msg

        try:
            WhatsAppLog.objects.create(
                user=session.user,
                phone_to=ADMIN_WHATSAPP_NUMBER,
                message=msg_logged,
                msg_type='alert',
                status='sent' if ok else 'failed',
                error_msg='' if ok else err,
            )
        except Exception:
            pass

    elif event_type == 'no_agent':
        # 1. Alert to Admin (2-minute timeout warning)
        admin_msg = (
            f"⏰ *Missed Live Chat (2-Min Timeout)*\n\n"
            f"No agent was able to join Session #{session.id} within 2 minutes.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Name:* {user_name}\n"
            f"📧 *Email:* {user_email}\n"
            f"📱 *Phone:* {phone}\n"
            f"🏷️ *Account:* {user_type}\n"
            f"🆔 *Session ID:* #{session.id}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👉 *Open Chat to Reply:*\n"
            f"https://voidonyx.in/super-admin/livechat/{session.id}/"
        )
        try:
            ok, err = _send_whatsapp_message(ADMIN_WHATSAPP_NUMBER, admin_msg)
            WhatsAppLog.objects.create(
                user=session.user,
                phone_to=ADMIN_WHATSAPP_NUMBER,
                message=admin_msg,
                msg_type='alert',
                status='sent' if ok else 'failed',
                error_msg='' if ok else err,
            )
        except Exception:
            pass

        # 2. Confirmation WhatsApp to Customer via approved template 'live_chat_busy_followup'
        if session.guest_phone:
            # Parameters: {{1}}=Name, {{2}}=Session ID
            c_ok, c_err = _send_whatsapp_template(
                session.guest_phone,
                'live_chat_busy_followup',
                [user_name, str(session.id)]
            )
            c_logged = f"[Template: live_chat_busy_followup] Follow-up for #{session.id} to {user_name}"

            if not c_ok:
                client_msg = (
                    f"Hi {user_name}! 👋\n\n"
                    f"We're sorry we couldn't connect with you immediately in live chat! 😔\n\n"
                    f"Our support team has received your request and contact details. An agent will get back to you as soon as possible via WhatsApp or email.\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📋 *Support Ticket Ref:* #{session.id}\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"Feel free to reply directly to this message if you have more details to share.\n\n"
                    f"Thank you for reaching out to VoidOnyx! ⭐\n"
                    f"— *VoidOnyx Support Team*"
                )
                c_ok, c_err = _send_whatsapp_message(session.guest_phone, client_msg)
                c_logged = client_msg

            try:
                WhatsAppLog.objects.create(
                    user=session.user,
                    phone_to=session.guest_phone,
                    message=c_logged,
                    msg_type='alert',
                    status='sent' if c_ok else 'failed',
                    error_msg='' if c_ok else c_err,
                )
            except Exception:
                pass


def _send_transcript_email(session):
    """Send a richly formatted HTML transcript email with any file attachments."""
    history_qs = session.messages.order_by('timestamp')

    user_display = session.user.email if session.user else f"{session.guest_name} ({session.guest_email})"
    user_email = session.user.email if session.user else session.guest_email
    phone_display = session.guest_phone or "Not provided"
    if session.user and not session.guest_phone:
        try:
            phone_display = session.user.customer_profile.phone or "Not provided"
        except Exception:
            pass
    agent_email = session.assigned_agent.email if session.assigned_agent else None
    agent_name = session.assigned_agent.username if session.assigned_agent else 'Unassigned'

    # Build the HTML message rows
    message_rows_html = ''
    for m in history_qs:
        ts = m.timestamp.strftime('%H:%M')
        is_agent = (m.sender_type == 'agent')
        align = 'right' if is_agent else 'left'
        bubble_bg = '#59c4bc' if is_agent else 'rgba(255,255,255,0.08)'
        bubble_color = '#041a18' if is_agent else '#e2eaf6'
        label = f"🛡️ Agent ({agent_name})" if is_agent else f"👤 {user_display}"
        border_radius = '14px 14px 2px 14px' if is_agent else '14px 14px 14px 2px'

        if m.msg_type == 'text':
            content_html = f'<div style="display:inline-block;background:{bubble_bg};color:{bubble_color};padding:10px 16px;border-radius:{border_radius};max-width:70%;font-size:0.88rem;word-break:break-word;">{m.content}</div>'
        elif m.msg_type == 'image':
            content_html = f'<div style="display:inline-block;"><img src="{m.attachment.url if m.attachment else ""}" alt="{m.attachment_name}" style="max-width:280px;border-radius:10px;border:1px solid rgba(89,196,188,0.3);" /></div>'
        else:
            content_html = f'<div style="display:inline-block;background:{bubble_bg};color:{bubble_color};padding:10px 16px;border-radius:{border_radius};font-size:0.85rem;">📎 <a href="{m.attachment.url if m.attachment else "#"}" style="color:#59c4bc;">{m.attachment_name or "Attachment"}</a></div>'

        message_rows_html += f"""
        <tr><td>
            <div style="text-align:{align};margin-bottom:18px;">
                <div style="font-size:0.7rem;color:#4d637e;margin-bottom:4px;">{label} &bull; {ts}</div>
                {content_html}
            </div>
        </td></tr>
        """

    html_body = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:620px;margin:auto;background:#070d18;color:#e2eaf6;border-radius:14px;overflow:hidden;border:1px solid rgba(89,196,188,0.2);">
        <div style="background:linear-gradient(135deg,#59c4bc,#3de0d5);padding:24px 28px;">
            <h2 style="margin:0;color:#041a18;">📋 Chat Transcript — Session #{session.id}</h2>
            <p style="margin:6px 0 0;color:rgba(4,26,24,0.75);font-size:0.88rem;">Conversation is now closed. Below is the full transcript.</p>
        </div>
        <div style="padding:20px 28px;">
            <table style="width:100%;border-collapse:collapse;margin-bottom:18px;">
                <tr><td style="padding:6px 0;color:#7a9ab5;font-size:0.8rem;width:120px;">User</td><td style="color:#e2eaf6;font-weight:600;">{user_display}</td></tr>
                <tr><td style="padding:6px 0;color:#7a9ab5;font-size:0.8rem;">Phone</td><td style="color:#59c4bc;font-weight:700;">{phone_display}</td></tr>
                <tr><td style="padding:6px 0;color:#7a9ab5;font-size:0.8rem;">Agent</td><td style="color:#e2eaf6;">{agent_name}</td></tr>
                <tr><td style="padding:6px 0;color:#7a9ab5;font-size:0.8rem;">Started</td><td style="color:#e2eaf6;">{session.created_at.strftime('%B %d, %Y at %H:%M UTC')}</td></tr>
                <tr><td style="padding:6px 0;color:#7a9ab5;font-size:0.8rem;">Closed</td><td style="color:#e2eaf6;">{session.updated_at.strftime('%B %d, %Y at %H:%M UTC')}</td></tr>
            </table>
            <hr style="border:none;border-top:1px solid rgba(255,255,255,0.06);margin:10px 0 20px;">
            <table style="width:100%;border-collapse:collapse;">
                {message_rows_html}
            </table>
        </div>
        <div style="background:rgba(255,255,255,0.03);padding:14px 28px;font-size:0.72rem;color:#4d637e;border-top:1px solid rgba(255,255,255,0.05);">
            VoidPanel Live Support &bull; This transcript was automatically generated.
        </div>
    </div>
    """

    recipients = list(set(filter(None, [user_email, agent_email])))
    if not recipients:
        return

    try:
        email_msg = EmailMessage(
            subject=f'📋 Chat Transcript — VoidPanel Session #{session.id}',
            body=html_body,
            from_email='VoidPanel Support <noreply@voidpanel.com>',
            to=recipients,
        )
        email_msg.content_subtype = 'html'

        # Attach any uploaded files from the session
        for m in history_qs:
            if m.attachment and m.msg_type in ('file', 'image'):
                try:
                    if m.attachment.name and os.path.exists(m.attachment.path):
                        email_msg.attach_file(m.attachment.path)
                except Exception:
                    pass

        email_msg.send(fail_silently=True)
    except Exception:
        pass


# ── API Endpoints ──────────────────────────────────────────────────────────────

@csrf_exempt
def chat_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        data = {}

    guest_name  = data.get('name', '').strip()
    guest_email = data.get('email', '').strip()
    guest_phone = data.get('phone', '').strip()

    # Normalise phone — auto-prepend +91 for 10-digit Indian numbers
    if guest_phone:
        digits_only = ''.join(filter(str.isdigit, guest_phone))
        if len(digits_only) == 10:
            guest_phone = '+91' + digits_only
        elif not guest_phone.startswith('+'):
            guest_phone = '+' + digits_only

    if request.user.is_authenticated:
        # Try to get registered user's phone if not provided
        reg_phone = guest_phone
        if not reg_phone:
            try:
                cp = getattr(request.user, 'customer_profile', None)
                raw = (cp.phone if cp else '') or ''
                digits_only = ''.join(filter(str.isdigit, str(raw)))
                if len(digits_only) == 10:
                    reg_phone = '+91' + digits_only
                elif digits_only:
                    reg_phone = '+' + digits_only if not str(raw).startswith('+') else str(raw)
            except Exception:
                pass
        session = LiveChatSession.objects.create(
            user=request.user,
            guest_phone=reg_phone,
            status='active'
        )
    else:
        # Guest users MUST provide Full Name, Email, and Phone Number
        if not guest_name or not guest_email or not guest_phone:
            return JsonResponse({'error': 'Full Name, Email Address, and Phone Number are required to start a chat.'}, status=400)
        session = LiveChatSession.objects.create(
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            status='active'
        )

    import threading
    threading.Thread(target=_send_new_chat_notification, args=(session,), daemon=True).start()
    threading.Thread(target=_send_chat_whatsapp_alert, args=(session, 'new_chat'), daemon=True).start()

    return JsonResponse({'status': 'ok', 'session_id': session.id})


@csrf_exempt
def chat_send(request, session_id):
    """Handle text messages and file/image uploads."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        session = LiveChatSession.objects.get(id=session_id)
    except LiveChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    if session.status == 'closed':
        return JsonResponse({'error': 'Session is closed'}, status=400)

    # Determine sender type
    is_agent = (
        request.user.is_authenticated
        and (request.user.is_staff or request.user.is_superuser)
        and session.assigned_agent == request.user
    )
    sender_type = 'agent' if is_agent else 'user'
    sender_user = request.user if request.user.is_authenticated else None

    # Check if this is a file upload (multipart) or JSON text
    if request.FILES.get('attachment'):
        uploaded = request.FILES['attachment']
        content_type = uploaded.content_type or ''
        msg_type = 'image' if content_type.startswith('image/') else 'file'
        LiveChatMessage.objects.create(
            session=session,
            sender_type=sender_type,
            sender_user=sender_user,
            msg_type=msg_type,
            content='',
            attachment=uploaded,
            attachment_name=uploaded.name,
        )
    else:
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': 'Invalid body'}, status=400)
        content = data.get('message', '').strip()
        if not content:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        LiveChatMessage.objects.create(
            session=session,
            sender_type=sender_type,
            sender_user=sender_user,
            msg_type='text',
            content=content,
        )

    return JsonResponse({'status': 'ok'})


@csrf_exempt
def chat_poll(request, session_id):
    try:
        session = LiveChatSession.objects.get(id=session_id)
    except LiveChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    last_msg_id = int(request.GET.get('last_id', 0))
    messages_qs = session.messages.filter(id__gt=last_msg_id).order_by('timestamp')

    msgs = []
    for m in messages_qs:
        item = {
            'id': m.id,
            'sender': m.sender_type,
            'msg_type': m.msg_type,
            'content': m.content,
            'timestamp': m.timestamp.strftime('%H:%M'),
            'attachment_name': m.attachment_name,
            'attachment_url': m.attachment.url if m.attachment else None,
        }
        msgs.append(item)

    return JsonResponse({
        'status': 'ok',
        'session_status': session.status,
        'messages': msgs,
        'assigned': session.assigned_agent.username if session.assigned_agent else None,
        'is_agent_assigned': bool(session.assigned_agent),
    })


@csrf_exempt
def chat_close(request, session_id):
    if request.method not in ('GET', 'POST'):
        return JsonResponse({'error': 'GET or POST required'}, status=405)
    try:
        session = LiveChatSession.objects.get(id=session_id)
    except LiveChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    if session.status != 'closed':
        session.status = 'closed'
        session.save()
        _send_transcript_email(session)

    return JsonResponse({'status': 'ok'})


@csrf_exempt
def chat_no_agent(request, session_id):
    """
    Called by the frontend after 2 minutes if no agent has joined.
    Sends email + WhatsApp notifications to admins and a follow-up
    WhatsApp message to the client asking them to elaborate their issue.
    """
    if request.method not in ('POST', 'GET'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        session = LiveChatSession.objects.get(id=session_id)
    except LiveChatSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)

    # Only fire once per session
    if session.no_agent_notified:
        return JsonResponse({'status': 'already_notified'})

    # Don't fire if an agent has already joined
    if session.assigned_agent:
        return JsonResponse({'status': 'agent_present'})

    session.no_agent_notified = True
    session.save(update_fields=['no_agent_notified'])

    # ── Determine user display info ──────────────────────────────────────────
    if session.user:
        user_display = session.user.get_full_name() or session.user.username
        user_email   = session.user.email
        user_type    = 'Registered'
    else:
        user_display = session.guest_name or 'Guest'
        user_email   = session.guest_email
        user_type    = 'Guest'

    client_phone = session.guest_phone or ''

    # ── Build HTML email body ────────────────────────────────────────────────
    html_body = f"""
    <div style="font-family:Inter,Arial,sans-serif;max-width:580px;margin:auto;background:#0f172a;color:#e2eaf6;border-radius:14px;overflow:hidden;border:1px solid rgba(239,68,68,0.3);">
        <div style="background:linear-gradient(135deg,#dc2626,#ef4444);padding:24px 28px;">
            <h2 style="margin:0;color:#fff;font-size:1.3rem;">⏰ Missed Live Chat — No Agent Joined</h2>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.8);font-size:0.9rem;">A user waited 2 minutes and no agent was available.</p>
        </div>
        <div style="padding:28px;">
            <table style="width:100%;border-collapse:collapse;">
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;width:130px;">Session ID</td><td style="color:#f87171;font-weight:700;">#{session.id}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Name</td><td style="color:#e2eaf6;font-weight:600;">{user_display}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Email</td><td style="color:#e2eaf6;">{user_email}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Phone</td><td style="color:#e2eaf6;">{client_phone or 'Not provided'}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">User Type</td><td style="color:#e2eaf6;">{user_type}</td></tr>
                <tr><td style="padding:8px 0;color:#7a9ab5;font-size:0.82rem;">Started</td><td style="color:#e2eaf6;">{session.created_at.strftime('%B %d, %Y at %H:%M UTC')}</td></tr>
            </table>
            <div style="margin-top:24px;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:16px;">
                <p style="margin:0;color:#fca5a5;font-size:0.85rem;">⚠️ Please follow up with this user as soon as possible. They wanted a live chat but no one was available.</p>
            </div>
            <div style="margin-top:20px;text-align:center;">
                <a href="https://voidpanel.com/super-admin/livechat/{session.id}/" style="display:inline-block;padding:12px 28px;background:#ef4444;color:#fff;font-weight:700;border-radius:8px;text-decoration:none;font-size:0.9rem;">
                    📋 View Session &rarr;
                </a>
            </div>
        </div>
        <div style="background:rgba(255,255,255,0.03);padding:14px 28px;font-size:0.72rem;color:#4d637e;border-top:1px solid rgba(255,255,255,0.05);">
            VoidPanel Live Support System &bull; Automated missed-chat notification.
        </div>
    </div>
    """

    # ── Send email to admins ─────────────────────────────────────────────────
    def _send_missed_chat_email():
        from data.models import OutboundEmailProfile
        from django.core.mail.backends.smtp import EmailBackend
        recipients = ['rohanfreakymg@gmail.com', 'contact@voidpanel.com']
        try:
            smtp_profile = (
                OutboundEmailProfile.objects
                .filter(is_active=True, send_on_live_chat=True)
                .order_by('-is_default')
                .first()
            )
        except Exception:
            smtp_profile = None
        try:
            if smtp_profile:
                email = EmailMessage(
                    subject=f'⏰ Missed Live Chat — Session #{session.id} — {user_display}',
                    body=html_body,
                    from_email=f'{smtp_profile.from_name or "VoidPanel Support"} <{smtp_profile.from_email}>',
                    to=recipients,
                    reply_to=[smtp_profile.reply_to_email] if smtp_profile.reply_to_email else [],
                )
                email.content_subtype = 'html'
                backend = EmailBackend(
                    host=smtp_profile.smtp_host,
                    port=smtp_profile.smtp_port,
                    username=smtp_profile.smtp_username,
                    password=smtp_profile.smtp_password,
                    use_tls=smtp_profile.use_tls,
                    use_ssl=smtp_profile.use_ssl,
                    fail_silently=False,
                )
                backend.open()
                backend.send_messages([email])
                backend.close()
            else:
                email = EmailMessage(
                    subject=f'⏰ Missed Live Chat — Session #{session.id} — {user_display}',
                    body=html_body,
                    from_email='VoidPanel Support <noreply@voidpanel.com>',
                    to=recipients,
                )
                email.content_subtype = 'html'
                email.send(fail_silently=True)
        except Exception:
            pass

    # Post beautiful reassuring agent message in the live chat stream
    busy_text = (
        "🙏 Sorry, we are currently assisting other customers! "
        "Our team has received your details and message. An agent will get back to you shortly via WhatsApp or email. "
        "Feel free to leave any additional questions or details here in the meantime!"
    )
    LiveChatMessage.objects.create(
        session=session,
        sender_type='agent',
        msg_type='text',
        content=busy_text
    )

    import threading
    threading.Thread(target=_send_missed_chat_email, daemon=True).start()
    threading.Thread(target=_send_chat_whatsapp_alert, args=(session, 'no_agent'), daemon=True).start()

    return JsonResponse({'status': 'ok', 'notified': True, 'message': busy_text})


@csrf_exempt
def admin_notify_poll(request):
    """
    Called by staff/admin pages every few seconds.
    Returns new user messages across all active sessions since last_id.
    Only accessible by authenticated staff/superusers.
    """
    if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    last_id = int(request.GET.get('last_id', 0))

    new_msgs = LiveChatMessage.objects.filter(
        id__gt=last_id,
        sender_type='user',
        session__status='active',
    ).select_related('session').order_by('id')

    alerts = []
    for m in new_msgs:
        sess = m.session
        user_label = sess.user.email if sess.user else f"{sess.guest_name} ({sess.guest_email})"
        alerts.append({
            'id': m.id,
            'session_id': sess.id,
            'user_label': user_label,
            'preview': m.content[:80] if m.msg_type == 'text' else f'[{m.msg_type}] {m.attachment_name}',
            'timestamp': m.timestamp.strftime('%H:%M'),
        })

    return JsonResponse({
        'status': 'ok',
        'alerts': alerts,
        'max_id': alerts[-1]['id'] if alerts else last_id,
    })
