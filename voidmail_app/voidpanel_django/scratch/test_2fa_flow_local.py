import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voidpanel_project.settings')
django.setup()

from django.contrib.auth.models import User
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from apps.core.auth_registration import check_login_step1, verify_2fa_key
from apps.mail_engine.models import UserTwoFactorProfile, UserSecurityKey
from apps.mail_engine.views import get_2fa_security_status_api, toggle_2fa_api, add_security_key_api, delete_security_key_api
import json

def setup_request(rf, method='POST', path='/', data=None, user=None):
    if method == 'POST':
        req = rf.post(path, data=json.dumps(data or {}), content_type='application/json')
    else:
        req = rf.get(path)
    
    # Attach session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(req)
    req.session.save()
    
    if user:
        req.user = user
    return req

def run_tests():
    rf = RequestFactory()
    
    # 1. Ensure test users
    normal_user, _ = User.objects.get_or_create(username='test_normal_user', defaults={'email': 'normal@voidonyx.com'})
    normal_user.set_password('TestPass123!')
    normal_user.save()
    
    # Make sure 2FA is disabled for normal user
    p_norm, _ = UserTwoFactorProfile.objects.get_or_create(user=normal_user)
    p_norm.is_2fa_enabled = False
    p_norm.save()
    normal_user.security_keys.all().delete()
    
    twofa_user, _ = User.objects.get_or_create(username='test_2fa_user', defaults={'email': 'twofa@voidonyx.com'})
    twofa_user.set_password('TestPass123!')
    twofa_user.save()
    
    # Ensure 2FA is enabled with a security key
    p_2fa, _ = UserTwoFactorProfile.objects.get_or_create(user=twofa_user)
    p_2fa.is_2fa_enabled = True
    p_2fa.save()
    
    twofa_user.security_keys.all().delete()
    key = UserSecurityKey.objects.create(
        user=twofa_user,
        name='MacBook Touch ID',
        key_type='touchid',
        credential_id='test_cred_123'
    )
    
    print('--- TEST 1: Normal User Login (Direct Sign-In) ---')
    req1 = setup_request(rf, 'POST', '/api/v1/auth/login-step1/', {
        'username': 'test_normal_user',
        'password': 'TestPass123!'
    })
    resp1 = check_login_step1(req1)
    data1 = json.loads(resp1.content.decode())
    print('Normal user response:', data1)
    assert data1['status'] == 'success'
    assert data1['requires_2fa'] is False
    assert '_auth_user_id' in req1.session, "Normal user should be directly authenticated in session"
    print('✓ Test 1 Passed: Normal user gets direct 1-step sign-in!')
    
    print('\n--- TEST 2: 2FA User Step 1 (Password Required First) ---')
    req2 = setup_request(rf, 'POST', '/api/v1/auth/login-step1/', {
        'username': 'test_2fa_user',
        'password': 'WrongPassword!'
    })
    resp2 = check_login_step1(req2)
    data2 = json.loads(resp2.content.decode())
    print('Wrong password response:', data2)
    assert data2['status'] == 'error'
    print('✓ Test 2A Passed: Wrong password rejected!')
    
    req2_ok = setup_request(rf, 'POST', '/api/v1/auth/login-step1/', {
        'username': 'test_2fa_user',
        'password': 'TestPass123!'
    })
    resp2_ok = check_login_step1(req2_ok)
    data2_ok = json.loads(resp2_ok.content.decode())
    print('2FA user Step 1 response:', data2_ok)
    assert data2_ok['status'] == 'success'
    assert data2_ok['requires_2fa'] is True
    assert len(data2_ok['keys']) == 1
    assert data2_ok['keys'][0]['name'] == 'MacBook Touch ID'
    assert '_auth_user_id' not in req2_ok.session, "2FA user must NOT have full auth session before step 2"
    assert req2_ok.session.get('2fa_pending_user_id') == twofa_user.id
    print('✓ Test 2B Passed: 2FA user password verified, pending session created, 2FA required!')
    
    print('\n--- TEST 3: 2FA User Step 2 (Security Key Verification) ---')
    # Use the session from Step 1
    req3 = rf.post('/api/v1/auth/2fa/verify-key/', data=json.dumps({'key_id': key.id}), content_type='application/json')
    req3.session = req2_ok.session
    req3.user = getattr(req2_ok, 'user', None)
    resp3 = verify_2fa_key(req3)
    data3 = json.loads(resp3.content.decode())
    print('Step 2 key verification response:', data3)
    assert data3['status'] == 'success'
    assert '_auth_user_id' in req3.session, "User must now have full authenticated session"
    assert req3.session['_auth_user_id'] == str(twofa_user.id)
    print('✓ Test 3 Passed: Security key verified, full login completed!')

    print('\n--- TEST 4: Security Center API (Status, Add Key, Toggle, Delete Key) ---')
    req_status = setup_request(rf, 'GET', '/mail/api/security/2fa/status/', user=twofa_user)
    resp_status = get_2fa_security_status_api(req_status)
    data_status = json.loads(resp_status.content.decode())
    print('Security status response:', data_status)
    assert data_status['status'] == 'success'
    assert data_status['is_2fa_enabled'] is True
    assert data_status['keys_count'] >= 1
    print('✓ Test 4A Passed: Security Center status API returned correct data!')

    # Add new key
    req_add = setup_request(rf, 'POST', '/mail/api/security/2fa/add-key/', {
        'name': 'Office YubiKey 5C',
        'key_type': 'security_key',
        'credential_id': 'yubikey_test_cred'
    }, user=twofa_user)
    resp_add = add_security_key_api(req_add)
    data_add = json.loads(resp_add.content.decode())
    print('Add key response:', data_add)
    assert data_add['status'] == 'success'
    assert data_add['key']['name'] == 'Office YubiKey 5C'
    print('✓ Test 4B Passed: New security key registered!')

    # Clean up test records
    normal_user.delete()
    twofa_user.delete()
    print('\nAll local tests completed successfully!')

if __name__ == '__main__':
    run_tests()
