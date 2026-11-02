from django.urls import path
from . import views
from . import auth_registration

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('register/', views.signup_view, name='register'),
    path('workspace/', views.workspace_view, name='workspace'),
    path('health/', views.health_check, name='health_check'),

    # Gmail-style registration & WhatsApp OTP verification
    path('api/v1/auth/check-username/', auth_registration.check_username_availability, name='api_check_username'),
    path('api/v1/auth/send-otp/', auth_registration.send_registration_otp, name='api_send_otp'),
    path('api/v1/auth/verify-and-register/', auth_registration.verify_otp_and_register, name='api_verify_register'),

    # Two-Factor Authentication & Login Steps
    path('api/v1/auth/login-step1/', auth_registration.check_login_step1, name='api_login_step1'),
    path('api/v1/auth/2fa/verify-key/', auth_registration.verify_2fa_key, name='api_verify_2fa_key'),
    path('api/v1/auth/2fa/send-whatsapp-otp/', auth_registration.send_2fa_whatsapp_otp, name='api_send_2fa_whatsapp_otp'),
    path('api/v1/auth/2fa/verify-whatsapp-otp/', auth_registration.verify_2fa_whatsapp_otp, name='api_verify_2fa_whatsapp_otp'),
    path('api/v1/auth/2fa/biometric-passkey/', auth_registration.biometric_passkey_login, name='api_biometric_passkey_login'),
]
