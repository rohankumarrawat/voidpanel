#!/usr/bin/env python3
import paramiko, time

HOST='fast.voidpanel.com'; PORT=22; USER='root'; PASS='19072002ROHANkumar!'

def connect():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, port=PORT, username=USER, password=PASS, timeout=10)
    return ssh

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

ssh = connect()
print("=== TEMPORARILY EDITING OPENDKIM.CONF FOR TEST ===")
run(ssh, "cp /etc/opendkim.conf /etc/opendkim.conf.bak")

basic_config = """Syslog                  yes
RequiredHeaders         yes
UMask                   007
Mode                    sv
Socket                  inet:8891@127.0.0.1
PidFile                 /run/opendkim/opendkim.pid
OversignHeaders         From
UserID                  opendkim

# KeyTable                /etc/opendkim/KeyTable
# SigningTable            refile:/etc/opendkim/SigningTable
ExternalIgnoreList      refile:/etc/opendkim/TrustedHosts
InternalHosts          refile:/etc/opendkim/TrustedHosts
"""
run(ssh, f"echo '{basic_config}' > /etc/opendkim.conf")

print("=== STARTING OPENDKIM ===")
run(ssh, "systemctl reset-failed opendkim")
run(ssh, "systemctl restart opendkim")
time.sleep(1.5)

print("=== OPENDKIM STATUS ===")
out, err = run(ssh, "systemctl status opendkim")
print(out)

print("=== RESTORING ORIGINAL CONFIG ===")
run(ssh, "mv /etc/opendkim.conf.bak /etc/opendkim.conf")
run(ssh, "systemctl restart opendkim")

ssh.close()
