import pexpect

child = pexpect.spawn('ssh -o StrictHostKeyChecking=no root@178.18.250.134', timeout=60, encoding='utf-8')
child.expect('password:')
child.sendline('19072002ROHANkumar')
child.expect('# ')

script = """
cd /var/www/panel
export PYTHONPATH=/var/www/panel/website/voidpanel
export DJANGO_SETTINGS_MODULE=panel.settings
python3 manage.py shell -c "
import os, threading
from control.models import domain, user
from function import zip_multiple_locations_backup_user
from voidplatform.config import paths

current = 'namanit'
namm=domain.objects.get(domain='namanitwork.tech')
main_directory = os.path.join(paths.HOME_BASE, namm.dir)
front=os.path.join(paths.HOME_BASE, namm.dir)

locations = [front]
zip_filename = 'test_backup_cli'
progress_file = os.path.join(main_directory, '.backup_progress')

print('Starting zip test...')
try:
    zip_multiple_locations_backup_user(main_directory, locations, zip_filename, current, progress_file)
    print('Zip test finished successfully.')
except Exception as e:
    import traceback
    print('Error caught:', e)
    traceback.print_exc()
"
"""

for line in script.strip().split('\n'):
    child.sendline(line)

child.expect('Zip test finished', timeout=30)
print(child.before.strip())
child.sendline('exit')
