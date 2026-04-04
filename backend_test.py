import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'panel.settings')
django.setup()
from django.test import Client
import json

client = Client()
client.login(username='macdomain.test', password='macpass123')

print("Testing Python App Provisioning...")
resp = client.post('/addpython/', data=json.dumps({'domain': 'macdomain.test', 'name': 'testpythonapp', 'port': '8005'}), content_type='application/json')
print(f"Python Add Response Status: {resp.status_code}")

print("Testing MERN App Provisioning...")
resp = client.post('/addmern/', data=json.dumps({'domain': 'macdomain.test', 'name': 'testmernapp'}), content_type='application/json')
print(f"MERN Add Response Status: {resp.status_code}")

print("Testing FTP Account Creation...")
resp = client.post('/control/ftpadd/', data=json.dumps({'username': 'newftp123', 'password': 'ftp_password', 'domain': 'macdomain.test'}), content_type='application/json')
print(f"FTP Add Response Status: {resp.status_code}")
