
# ── Support Ticket System (Proxy to voidpanel.com) ──────────────────────────

import requests

VOIDPANEL_API_URL = "https://voidpanel.com"

def get_license_key_value():
    from control.license import get_license
    lic = get_license()
    if lic and lic.status == 'active':
        return lic.key
    return None

@login_required(login_url='/')
def support_page(request):
    """Render the local support ticket interface."""
    if not request.user.is_superuser:
        return redirect('/')
    return render(request, 'panel/support.html')

@login_required(login_url='/')
@csrf_exempt
def api_ticket_create(request):
    """POST /api/tickets/create/ (Proxies to voidpanel.com)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)
        
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'error', 'message': 'No active license found. Cannot submit ticket.'}, status=400)

    payload = {
        'license_key': license_key,
        'subject': data.get('subject', '').strip(),
        'department': data.get('department', 'Technical Support'),
        'priority': data.get('priority', 'medium'),
        'body': data.get('message', '').strip()
    }

    if not payload['subject'] or not payload['body']:
        return JsonResponse({'status': 'error', 'message': 'Subject and message are required'}, status=400)

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/create/", json=payload, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            return JsonResponse({'status': 'success', 'ticket_id': resp.get('ticket_number')})
        else:
            return JsonResponse({'status': 'error', 'message': resp.get('error', 'Failed to create ticket on VoidPanel.com')})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


@login_required(login_url='/')
def api_ticket_list(request):
    """GET /api/tickets/list/ (Proxies to voidpanel.com)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error'}, status=403)
        
    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'success', 'tickets': []})

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/list/", json={'license_key': license_key}, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            tickets = resp.get('tickets', [])
            for t in tickets:
                t['ticket_id'] = t.get('ticket_number')
                t['message'] = t.get('body', 'No message body provided.')
                t['created_at'] = t.get('created_at', t.get('last_reply_at', 'Unknown'))
            return JsonResponse({'status': 'success', 'tickets': tickets})
        else:
            return JsonResponse({'status': 'error', 'message': resp.get('error', 'Error fetching tickets')})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


@login_required(login_url='/')
def api_ticket_detail(request, ticket_id):
    """GET /api/tickets/<ticket_id>/ (Pulls from list proxy)"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error'}, status=403)
        
    license_key = get_license_key_value()
    if not license_key:
        return JsonResponse({'status': 'error', 'message': 'No license'}, status=400)

    try:
        r = requests.post(f"{VOIDPANEL_API_URL}/api/panel/ticket/list/", json={'license_key': license_key}, timeout=15)
        resp = r.json()
        if resp.get('ok'):
            tickets = resp.get('tickets', [])
            for t in tickets:
                if str(t.get('ticket_number')) == str(ticket_id):
                    return JsonResponse({
                        'status': 'success',
                        'ticket': {
                            'ticket_id': t.get('ticket_number'),
                            'subject': t.get('subject'),
                            'department': t.get('department'),
                            'priority': t.get('priority'),
                            'status': t.get('status'),
                            'message': t.get('body', 'Message hidden.'),
                            'created_by': 'You',
                            'created_at': t.get('created_at', t.get('last_reply_at', 'Unknown')),
                        },
                        'replies': t.get('replies', [])
                    })
            return JsonResponse({'status': 'error', 'message': 'Ticket not found'})
        return JsonResponse({'status': 'error', 'message': 'Error fetching ticket'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': 'Could not reach VoidPanel.com API'})


@login_required(login_url='/')
@csrf_exempt
def api_ticket_reply(request, ticket_id):
    """POST /api/tickets/<ticket_id>/reply/"""
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error'}, status=403)
    return JsonResponse({'status': 'error', 'message': 'Reply feature coming soon. Please use the VoidPanel.com portal to reply for now.'}, status=400)
