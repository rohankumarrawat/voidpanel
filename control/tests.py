import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from control.models import MarketingTemplate, MarketingCampaign, CampaignRecipient, PanelLicense
from django.utils import timezone

class MarketingTestCase(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username='admin', password='adminpassword')
        
        # Create active license to bypass LicenseMiddleware
        PanelLicense.objects.create(
            key='dummykeydummykeydummykeydummykeydummy',
            status='active',
            issued_at=timezone.now(),
            last_checked=timezone.now()
        )
        
        # Setup client
        self.client = Client()
        self.client.login(username='admin', password='adminpassword')
        
        self.domain = 'test.com'

    def test_save_new_template(self):
        payload = {
            'name': 'Welcome Template',
            'subject': 'Welcome to voidpanel!',
            'content_html': '<h1>Welcome!</h1>',
            'content_json': json.dumps([{'type': 'header', 'content': 'Welcome!'}])
        }
        
        response = self.client.post(
            f'/control/marketing/{self.domain}/template/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get('status'), 'saved')
        
        tmpl = MarketingTemplate.objects.get(id=data.get('id'))
        self.assertEqual(tmpl.name, 'Welcome Template')

    def test_update_existing_template(self):
        tmpl = MarketingTemplate.objects.create(
            user=self.user, domain=self.domain,
            name='Old Title', subject='Old Sub',
            content_html='<p>old</p>', content_json='[]'
        )
        
        payload = {
            'id': tmpl.id,
            'name': 'Updated Title',
            'subject': 'Updated Sub',
            'content_html': '<p>new</p>',
            'content_json': '[{"type":"text"}]'
        }
        
        response = self.client.post(
            f'/control/marketing/{self.domain}/template/save/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        tmpl.refresh_from_db()
        self.assertEqual(tmpl.name, 'Updated Title')

    def test_list_templates(self):
        MarketingTemplate.objects.create(
            user=self.user, domain=self.domain,
            name='Custom One', subject='Sub',
            content_html='<p>hi</p>', content_json='[]'
        )
        
        response = self.client.get(f'/control/marketing/{self.domain}/templates/list/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['custom_templates']), 1)

    def test_campaign_details_and_delete(self):
        # Create a test campaign
        camp = MarketingCampaign.objects.create(
            user=self.user, domain=self.domain,
            name='Summer Promo', channel='email',
            subject='Save big!', sender_email='promo@test.com',
            body='Promo content', status='sent'
        )
        
        # Create a recipient
        CampaignRecipient.objects.create(
            campaign=camp, email='customer@example.com',
            name='John Doe', status='opened'
        )

        # Get details
        response = self.client.get(f'/control/marketing/{self.domain}/campaign/{camp.id}/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['campaign']['name'], 'Summer Promo')
        self.assertEqual(data['analytics']['total'], 1)
        self.assertEqual(data['analytics']['opened'], 1)
        self.assertEqual(len(data['recipients']), 1)
        self.assertEqual(data['recipients'][0]['name'], 'John Doe')

        # Delete campaign
        delete_response = self.client.post(f'/control/marketing/{self.domain}/campaign/{camp.id}/delete/')
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json().get('status'), 'deleted')

        # Ensure deleted from DB
        self.assertFalse(MarketingCampaign.objects.filter(id=camp.id).exists())
        self.assertFalse(CampaignRecipient.objects.filter(campaign=camp).exists())

    def test_campaign_pause_and_resume(self):
        # Create a scheduled campaign
        camp = MarketingCampaign.objects.create(
            user=self.user, domain=self.domain,
            name='Winter Promo', channel='email',
            subject='Save!', sender_email='promo@test.com',
            body='Promo content', status='scheduled',
            scheduled_at=timezone.now() + timezone.timedelta(days=1)
        )
        
        # Test pausing
        response = self.client.post(
            f'/control/marketing/{self.domain}/campaign/{camp.id}/toggle-status/',
            data=json.dumps({'action': 'pause'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        camp.refresh_from_db()
        self.assertEqual(camp.status, 'paused')

        # Test resuming
        response = self.client.post(
            f'/control/marketing/{self.domain}/campaign/{camp.id}/toggle-status/',
            data=json.dumps({'action': 'resume'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        camp.refresh_from_db()
        self.assertEqual(camp.status, 'scheduled')

    def test_sms_gateway_save_and_test(self):
        from control.models import SMSGatewayConfig
        # Save config
        save_response = self.client.post(
            f'/control/marketing/{self.domain}/sms/gateway/save/',
            data=json.dumps({
                'provider': 'twilio',
                'api_key': 'ACtestapikey123',
                'api_secret': 'authsecrettoken',
                'sender_id': '+1234567890'
            }),
            content_type='application/json'
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(save_response.json().get('status'), 'saved')
        
        # Verify saved in DB
        self.assertTrue(SMSGatewayConfig.objects.filter(
            user=self.user, domain=self.domain, provider='twilio', api_key='ACtestapikey123'
        ).exists())

        # Test gateway connection check (mock checking)
        test_response = self.client.post(
            f'/control/marketing/{self.domain}/sms/gateway/test/',
            data=json.dumps({
                'provider': 'vonage',
                'api_key': 'vonagekey',
                'api_secret': 'vonagesecret',
                'sender_id': 'VONAGE'
            }),
            content_type='application/json'
        )
        self.assertEqual(test_response.status_code, 200)
        self.assertEqual(test_response.json().get('status'), 'success')

    def test_whatsapp_settings_and_web_simulate(self):
        # 1. Save WhatsApp Cloud API Config
        save_response = self.client.post(
            f'/control/marketing/{self.domain}/settings/whatsapp/save/',
            data=json.dumps({
                'provider': 'meta',
                'phone_id': '1049283749281',
                'access_token': 'EAAKdBx8vC7...'
            }),
            content_type='application/json'
        )
        self.assertEqual(save_response.status_code, 200)
        self.assertEqual(save_response.json().get('status'), 'success')

        # 2. Check initial WhatsApp Web status (should be disconnected)
        status_response = self.client.get(f'/control/marketing/{self.domain}/settings/whatsapp-web/status/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json().get('status'), 'disconnected')

        # 3. Simulate scan and connect
        connect_response = self.client.post(f'/control/marketing/{self.domain}/settings/whatsapp-web/simulate-connect/')
        self.assertEqual(connect_response.status_code, 200)
        self.assertEqual(connect_response.json().get('status'), 'success')

        # 4. Check status again (should be connected)
        status_response = self.client.get(f'/control/marketing/{self.domain}/settings/whatsapp-web/status/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json().get('status'), 'connected')

        # 5. Disconnect WhatsApp Web
        disconnect_response = self.client.post(f'/control/marketing/{self.domain}/settings/whatsapp-web/disconnect/')
        self.assertEqual(disconnect_response.status_code, 200)
        self.assertEqual(disconnect_response.json().get('status'), 'success')

        # 6. Check final status (should be disconnected)
        status_response = self.client.get(f'/control/marketing/{self.domain}/settings/whatsapp-web/status/')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json().get('status'), 'disconnected')

    def test_whatsapp_web_qr_auth_flow(self):
        # 1. GET mobile auth page
        get_response = self.client.get(f'/control/marketing/{self.domain}/settings/whatsapp-web/qr-auth/?session=voidpanel-wa-link-12345')
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'Link WhatsApp Device')
        self.assertContains(get_response, 'voidpanel-wa-link-12345')

        # 2. POST to approve link
        post_response = self.client.post(
            f'/control/marketing/{self.domain}/settings/whatsapp-web/qr-auth/',
            data=json.dumps({
                'action': 'approve',
                'session_id': 'voidpanel-wa-link-12345',
                'device_name': 'iPhone 15 Pro (Safari)'
            }),
            content_type='application/json'
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertEqual(post_response.json().get('status'), 'success')

        # 3. Check status (should be connected)
        status_response = self.client.get(f'/control/marketing/{self.domain}/settings/whatsapp-web/status/')
        self.assertEqual(status_response.json().get('status'), 'connected')
        self.assertEqual(status_response.json().get('device'), 'iPhone 15 Pro (Safari)')

    def test_seo_suite_flow(self):
        # 1. GET SEO Suite Dashboard
        get_response = self.client.get(f'/control/seo/{self.domain}/')
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, 'SEO Center')

        # 2. POST to analyze domain
        post_response = self.client.post(
            f'/control/seo/{self.domain}/analyze/',
            data=json.dumps({
                'domain': 'google.com'
            }),
            content_type='application/json'
        )
        self.assertEqual(post_response.status_code, 200)
        data = post_response.json()
        self.assertEqual(data.get('status'), 'success')
        self.assertIn('metrics', data.get('data'))
        self.assertIn('keywords', data.get('data'))
        self.assertIn('backlinks', data.get('data'))
