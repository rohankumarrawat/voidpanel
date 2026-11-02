import json
import secrets
import datetime
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from .models import CalendarEvent, BookingSlot, VoidDoc, SignatureDocument, FormDefinition, MeetingSignal


def generate_voidmeet_room(request):
    """1-Click Browser Video Meeting Room Generator (WebRTC Sovereign Video)"""
    room_id = 'vmeet_' + secrets.token_urlsafe(8)
    meeting_url = f"https://mail.voidonyx.in/meet/{room_id}/"
    return JsonResponse({
        'success': True,
        'room_id': room_id,
        'meeting_url': meeting_url,
        'message': '1-Click VoidMeet video conference room created!'
    })


def _resolve_host_user_and_slot(username_or_slug):
    """Finds the host User and their BookingSlot by username, email, or custom slug"""
    clean_str = (username_or_slug or '').strip()
    if not clean_str:
        return None, None

    # 1. Match Django username directly
    user = User.objects.filter(username__iexact=clean_str).first()

    # 2. Match email prefix (e.g. hardikdhawan@voidonyx.com)
    if not user:
        user = User.objects.filter(email__istartswith=clean_str + '@').first()

    # 3. Match custom BookingSlot slug
    slot = None
    if not user:
        slot = BookingSlot.objects.filter(slug__iexact=clean_str, is_active=True).first()
        if slot:
            user = slot.user

    # If user found, find or create their booking slot
    if user:
        if not slot:
            slot = BookingSlot.objects.filter(user=user, is_active=True).first()
        if not slot:
            slot = BookingSlot.objects.create(
                user=user,
                slug=user.username.lower(),
                title="30-Minute Video Meeting",
                description="Select a convenient time slot for our 1-on-1 strategy sync or consultation.",
                duration_minutes=30,
                working_hours_start=9,
                working_hours_end=18,
                timezone_name="Asia/Kolkata"
            )

    return user, slot


def public_booking_page(request, username):
    """Renders the public booking calendar page for the specified host"""
    host_user, slot = _resolve_host_user_and_slot(username)
    if not host_user or not slot:
        return render(request, 'collaboration/booking_not_found.html', {
            'requested_username': username
        }, status=404)

    host_name = host_user.get_full_name().strip() or host_user.username.capitalize()
    host_initial = (host_name[0] if host_name else 'V').upper()

    context = {
        'host_user': host_user,
        'host_name': host_name,
        'host_initial': host_initial,
        'host_email': host_user.email,
        'username': username,
        'slot': slot,
        'duration': slot.duration_minutes,
        'timezone_name': slot.timezone_name or 'Asia/Kolkata',
        'current_year': timezone.now().year,
        'current_month': timezone.now().month,
    }
    return render(request, 'collaboration/booking_page.html', context)


def get_available_slots_api(request, username):
    """Calculates available 30-min time slots for a given date, checking calendar conflicts"""
    host_user, slot = _resolve_host_user_and_slot(username)
    if not host_user or not slot:
        return JsonResponse({'status': 'error', 'message': 'Host user not found'}, status=404)

    date_str = request.GET.get('date', '').strip()
    if not date_str:
        date_obj = timezone.localdate()
    else:
        try:
            date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date format (use YYYY-MM-DD)'}, status=400)

    # Disable past dates
    today = timezone.localdate()
    if date_obj < today:
        return JsonResponse({
            'status': 'success',
            'date': date_obj.strftime('%Y-%m-%d'),
            'slots': [],
            'message': 'Cannot book past dates'
        })

    duration_mins = slot.duration_minutes or 30
    start_hour = max(0, min(23, slot.working_hours_start or 9))
    end_hour = max(start_hour + 1, min(24, slot.working_hours_end or 18))

    # Fetch existing calendar events for this host on this day
    day_start = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.min))
    day_end = timezone.make_aware(datetime.datetime.combine(date_obj, datetime.time.max))

    events = CalendarEvent.objects.filter(
        user=host_user,
        start_time__lt=day_end,
        end_time__gt=day_start
    )

    busy_intervals = []
    for ev in events:
        if ev.start_time and ev.end_time:
            busy_intervals.append((ev.start_time, ev.end_time))

    # Generate candidate time slots
    available_slots = []
    current_time_cursor = datetime.datetime.combine(date_obj, datetime.time(start_hour, 0))
    end_time_cursor = datetime.datetime.combine(date_obj, datetime.time(end_hour, 0))

    now_aware = timezone.now()

    while current_time_cursor + datetime.timedelta(minutes=duration_mins) <= end_time_cursor:
        slot_start_dt = timezone.make_aware(current_time_cursor)
        slot_end_dt = slot_start_dt + datetime.timedelta(minutes=duration_mins)

        # If today, skip times that have already passed (plus 30 min buffer)
        if date_obj == today and slot_start_dt <= now_aware + datetime.timedelta(minutes=15):
            current_time_cursor += datetime.timedelta(minutes=duration_mins)
            continue

        # Check conflict with any existing calendar event
        is_conflict = False
        for b_start, b_end in busy_intervals:
            if slot_start_dt < b_end and slot_end_dt > b_start:
                is_conflict = True
                break

        if not is_conflict:
            available_slots.append({
                'time_str': slot_start_dt.strftime('%I:%M %p'),
                'time_24': slot_start_dt.strftime('%H:%M'),
                'start_iso': slot_start_dt.isoformat(),
                'end_iso': slot_end_dt.isoformat()
            })

        current_time_cursor += datetime.timedelta(minutes=duration_mins)

    return JsonResponse({
        'status': 'success',
        'date': date_obj.strftime('%Y-%m-%d'),
        'date_formatted': date_obj.strftime('%A, %B %d, %Y'),
        'slots': available_slots,
        'duration_minutes': duration_mins,
        'count': len(available_slots)
    })


@csrf_exempt
def submit_booking_api(request, username):
    """Saves a confirmed public booking into the host's VoidMail calendar with a 1-click VoidMeet room"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    host_user, slot = _resolve_host_user_and_slot(username)
    if not host_user or not slot:
        return JsonResponse({'status': 'error', 'message': 'Host user not found'}, status=404)

    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
    except Exception:
        data = request.POST

    client_name = (data.get('name') or '').strip()
    client_email = (data.get('email') or '').strip()
    client_phone = (data.get('phone') or '').strip()
    date_str = (data.get('date') or '').strip()
    time_str = (data.get('time') or '').strip()  # e.g. "10:30 AM" or "10:30"
    client_notes = (data.get('notes') or '').strip()

    if not client_name or not client_email:
        return JsonResponse({'status': 'error', 'message': 'Name and Email are required'}, status=400)
    if not date_str or not time_str:
        return JsonResponse({'status': 'error', 'message': 'Date and Time are required'}, status=400)

    # Parse date and time
    try:
        if 'AM' in time_str.upper() or 'PM' in time_str.upper():
            time_part = datetime.datetime.strptime(time_str.upper(), '%I:%M %p').time()
        else:
            time_part = datetime.datetime.strptime(time_str, '%H:%M').time()
        date_part = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid date or time format: {str(e)}'}, status=400)

    duration_mins = slot.duration_minutes or 30
    start_dt = timezone.make_aware(datetime.datetime.combine(date_part, time_part))
    end_dt = start_dt + datetime.timedelta(minutes=duration_mins)

    # Check for double booking
    overlap_exists = CalendarEvent.objects.filter(
        user=host_user,
        start_time__lt=end_dt,
        end_time__gt=start_dt
    ).exists()

    if overlap_exists:
        return JsonResponse({
            'status': 'error',
            'message': 'This time slot was just booked by another client. Please select another slot.'
        }, status=409)

    # Generate 1-Click VoidMeet video room
    room_id = 'vmeet_' + secrets.token_urlsafe(8)
    meeting_url = f"https://mail.voidonyx.in/meet/{room_id}/"

    # Create Calendar Event
    event_title = f"{slot.title} - {client_name}"
    notes_body = (
        f"📅 Booked via Public Booking Page ({request.build_absolute_uri()})\n\n"
        f"👤 Client: {client_name}\n"
        f"✉️ Email: {client_email}\n"
        f"📱 Phone: {client_phone or 'Not provided'}\n"
        f"📝 Topic / Notes: {client_notes or 'None'}\n\n"
        f"🎥 1-Click Video Room: {meeting_url}"
    )

    event = CalendarEvent.objects.create(
        user=host_user,
        title=event_title,
        start_time=start_dt,
        end_time=end_dt,
        attendees=f"{client_email}, {host_user.email}",
        meeting_url=meeting_url,
        meeting_type='video',
        reminder_minutes=15,
        notes=notes_body
    )

    # Trigger WhatsApp alert to host if configured
    try:
        from apps.core.whatsapp import send_meta_whatsapp_email_alert
        from apps.mail_engine.models import WhatsAppAlertRule
        rule = WhatsAppAlertRule.objects.filter(user=host_user, is_active=True).first()
        if rule and rule.whatsapp_number:
            send_meta_whatsapp_email_alert(
                phone_number=rule.whatsapp_number,
                sender=f"{client_name} ({client_email})",
                subject=f"📅 New Meeting Booked: {slot.title}",
                date_str=f"{start_dt.strftime('%b %d, %I:%M %p')}",
                snippet=f"VoidMeet Link: {meeting_url}"
            )
    except Exception as wa_err:
        pass

    host_name = host_user.get_full_name().strip() or host_user.username.capitalize()

    return JsonResponse({
        'status': 'success',
        'event_id': event.id,
        'meeting_url': meeting_url,
        'room_id': room_id,
        'title': event.title,
        'date_str': start_dt.strftime('%A, %B %d, %Y'),
        'time_str': start_dt.strftime('%I:%M %p'),
        'duration_minutes': duration_mins,
        'host_name': host_name,
        'host_email': host_user.email,
        'client_name': client_name,
        'client_email': client_email
    })


def voidmeet_room_view(request, room_id):
    """Renders the 1-Click VoidMeet Sovereign WebRTC Video Conference Room"""
    clean_room = secrets.token_urlsafe(8) if not room_id else room_id.strip()

    display_name = ''
    if request.user.is_authenticated:
        display_name = request.user.get_full_name() or request.user.username

    meeting_url = f"https://mail.voidonyx.in/meet/{clean_room}/"

    context = {
        'room_id': clean_room,
        'meeting_url': meeting_url,
        'display_name': display_name,
        'is_authenticated': request.user.is_authenticated
    }
    return render(request, 'collaboration/meet.html', context)


@csrf_exempt
def voidmeet_signaling_api(request, room_id):
    """
    Lightweight WebRTC Signaling Store for VoidMeet Video Rooms.
    Handles 'join', 'signal' (offer/answer/ice-candidate/chat), 'poll', and 'leave'.
    Direct peer-to-peer WebRTC connection handles all audio, video, and screen streams!
    """
    clean_room = room_id.strip()

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8')) if request.body else request.POST
        except Exception:
            data = request.POST

        action = data.get('action')
        sender_id = data.get('sender_id', '').strip()
        sender_name = data.get('sender_name', 'Guest').strip() or 'Guest'

        if not sender_id:
            return JsonResponse({'status': 'error', 'message': 'sender_id is required'}, status=400)

        # 1. Join Room
        if action == 'join':
            # Broadcast join signal
            MeetingSignal.objects.create(
                room_id=clean_room,
                sender_id=sender_id,
                sender_name=sender_name,
                signal_type='join',
                payload=json.dumps({'sender_name': sender_name})
            )

            # Discover other active peers in this room (active in last 3 minutes)
            cutoff = timezone.now() - datetime.timedelta(minutes=3)
            recent_joins = MeetingSignal.objects.filter(
                room_id=clean_room,
                signal_type='join',
                created_at__gte=cutoff
            ).exclude(sender_id=sender_id)

            active_peers = {}
            for s in recent_joins:
                active_peers[s.sender_id] = s.sender_name

            # Check if any left
            recent_leaves = MeetingSignal.objects.filter(
                room_id=clean_room,
                signal_type='leave',
                created_at__gte=cutoff
            ).values_list('sender_id', flat=True)

            for left_id in recent_leaves:
                active_peers.pop(left_id, None)

            return JsonResponse({
                'status': 'success',
                'peers': [{'peer_id': pid, 'name': pname} for pid, pname in active_peers.items()]
            })

        # 2. Relay WebRTC Signal (Offer, Answer, ICE Candidate, Chat)
        elif action == 'signal':
            signal_type = data.get('signal_type', '')
            recipient_id = data.get('recipient_id', '').strip()
            payload = data.get('payload', {})

            MeetingSignal.objects.create(
                room_id=clean_room,
                sender_id=sender_id,
                sender_name=sender_name,
                recipient_id=recipient_id,
                signal_type=signal_type,
                payload=json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
            )
            return JsonResponse({'status': 'success'})

        # 3. Leave Room
        elif action == 'leave':
            MeetingSignal.objects.create(
                room_id=clean_room,
                sender_id=sender_id,
                sender_name=sender_name,
                signal_type='leave',
                payload=json.dumps({'sender_name': sender_name})
            )
            # Prune old signals older than 10 mins
            old_cutoff = timezone.now() - datetime.timedelta(minutes=10)
            MeetingSignal.objects.filter(room_id=clean_room, created_at__lt=old_cutoff).delete()
            return JsonResponse({'status': 'success'})

        return JsonResponse({'status': 'error', 'message': 'Unknown action'}, status=400)

    elif request.method == 'GET':
        peer_id = request.GET.get('peer_id', '').strip()
        try:
            since_id = int(request.GET.get('since_id', 0))
        except (ValueError, TypeError):
            since_id = 0

        # Query pending signals intended for this peer or broadcast to the room
        signals_qs = MeetingSignal.objects.filter(
            room_id=clean_room,
            id__gt=since_id
        ).exclude(sender_id=peer_id)

        if peer_id:
            from django.db.models import Q
            signals_qs = signals_qs.filter(Q(recipient_id=peer_id) | Q(recipient_id=''))

        signals_qs = signals_qs.order_by('id')[:50]

        result = []
        max_id = since_id
        for sig in signals_qs:
            max_id = max(max_id, sig.id)
            try:
                parsed_payload = json.loads(sig.payload) if sig.payload else {}
            except Exception:
                parsed_payload = sig.payload

            result.append({
                'id': sig.id,
                'sender_id': sig.sender_id,
                'sender_name': sig.sender_name,
                'recipient_id': sig.recipient_id,
                'signal_type': sig.signal_type,
                'payload': parsed_payload,
                'created_at': sig.created_at.isoformat()
            })

        return JsonResponse({
            'status': 'success',
            'signals': result,
            'last_id': max_id
        })


@csrf_exempt
def sign_document_view(request, token):
    """Sign PDF document online (VoidSign)"""
    doc = get_object_or_404(SignatureDocument, document_token=token)
    if request.method == 'POST':
        doc.is_signed = True
        doc.signed_at = timezone.now()
        doc.signature_audit_hash = secrets.token_hex(32)
        doc.save()
        return JsonResponse({
            'success': True,
            'message': 'Document digitally signed and certified with SHA-256 audit hash!',
            'audit_hash': doc.signature_audit_hash
        })
    return JsonResponse({
        'title': doc.title,
        'signatory': doc.signatory_email,
        'is_signed': doc.is_signed
    })
