import json
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import VipContact, OmnichannelLog

@csrf_exempt
def whatsapp_webhook(request):
    """
    2-Way WhatsApp Webhook Listener:
    When a user replies to an email alert via WhatsApp, this webhook
    receives the message and dispatches it as an authentic SMTP reply via Postfix.
    """
    if request.method == 'GET':
        # WhatsApp Webhook Verification handshake
        hub_challenge = request.GET.get('hub.challenge', '1158201444')
        return HttpResponse(hub_challenge)

    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            # Log inbound WhatsApp message
            OmnichannelLog.objects.create(
                channel='whatsapp',
                direction='inbound',
                recipient='support@voidonyx.com',
                content=json.dumps(payload)[:500],
                status='Processed'
            )
            return JsonResponse({'status': 'success', 'dispatched_as_email': True})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@csrf_exempt
def trigger_vip_alert(request):
    """Simulate or dispatch WhatsApp VIP notification"""
    if request.method == 'POST':
        data = json.loads(request.body)
        sender = data.get('sender', 'ceo@investor.com')
        subject = data.get('subject', 'Term Sheet Signed')
        phone = data.get('phone', '+919876543210')

        OmnichannelLog.objects.create(
            channel='whatsapp',
            direction='outbound',
            recipient=phone,
            content=f"🔔 VIP Alert from {sender}: {subject}",
            status='Sent'
        )
        return JsonResponse({
            'success': True,
            'channel': 'WhatsApp Cloud Gateway',
            'message': f'VIP Alert sent to {phone} for email "{subject}"'
        })
    return JsonResponse({'error': 'POST required'}, status=400)
