import subprocess
print("Running SSH...")
cmd = ["sshpass", "-p", "19072002ROHANkumar", "ssh", "-o", "StrictHostKeyChecking=no", "root@178.18.250.134", "journalctl -u voidpanel --no-pager -n 50"]
res = subprocess.run(cmd, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
