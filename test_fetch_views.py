import subprocess
print("Fetching views...")
cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "root@178.18.250.134", "cat /var/www/panel/panel/views.py"]
# I need to use pexpect or ssh keys. I have SSH key auth since I'm running locally? Let's check!
