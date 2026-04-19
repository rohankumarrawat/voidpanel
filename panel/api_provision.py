from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from django.conf import settings
from panel.logger import get_logger
import threading
from panel.views import background_create_account

logger = get_logger(__name__)

# Fallback config key
VOIDPANEL_API_KEY = getattr(settings, 'VOIDPANEL_API_KEY', 'change-me-in-settings')

def authenticate_request(request):
    """Authenticate incoming webhook from the front-end portal."""
    key = request.headers.get('X-VoidPanel-Key')
    if not key or key != VOIDPANEL_API_KEY:
        return False
    return True

@api_view(['POST'])
@permission_classes([AllowAny])
def portal_provision_create(request):
    if not authenticate_request(request):
        return Response({'status': 'error', 'message': 'Invalid API Key'}, status=403)
        
    domain = request.data.get('domain')
    email = request.data.get('email')
    package = request.data.get('package')
    
    if not domain or not package:
        return Response({'status': 'error', 'message': 'Missing domain or package'}, status=400)
    
    import secrets
    import string
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(16))
    
    import re
    username = re.sub(r'[^a-z0-9]', '', domain.split('.')[0].lower())[:9] + secrets.token_hex(2)
    
    thread = threading.Thread(
        target=background_create_account,
        args=(username, password, domain, package)
    )
    thread.start()
    
    return Response({
        'status': 'success', 
        'message': 'Account provision queued',
        'username': username,
        'panel_url': f"http://{domain}:8080" # Temporary convention
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def portal_provision_suspend(request):
    if not authenticate_request(request):
        return Response({'status': 'error', 'message': 'Invalid API Key'}, status=403)
    domain = request.data.get('domain')
    
    from control.tasks import suspend_user_task
    try:
        from control.models import user
        u = user.objects.get(domain=domain)
        suspend_user_task.delay(u.username, domain)
        return Response({'status': 'success', 'message': 'Account suspended'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def portal_provision_unsuspend(request):
    if not authenticate_request(request):
        return Response({'status': 'error', 'message': 'Invalid API Key'}, status=403)
    domain = request.data.get('domain')
    
    from control.tasks import unsuspend_user_task
    try:
        from control.models import user
        u = user.objects.get(domain=domain)
        unsuspend_user_task.delay(u.username, domain)
        return Response({'status': 'success', 'message': 'Account unsuspended'})
    except Exception as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)
