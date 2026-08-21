import socket, sys

host = "fast.voidpanel.com"
port = 22

print(f"Resolving {host}...")
try:
    ip = socket.gethostbyname(host)
    print(f"IP: {ip}")
except Exception as e:
    print(f"DNS Resolution failed: {e}")
    sys.exit(1)

print(f"Testing TCP connection to {ip}:{port}...")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
try:
    s.connect((ip, port))
    print("TCP connection successful!")
    banner = s.recv(1024)
    print(f"SSH Banner: {banner.decode().strip()}")
    s.close()
except Exception as e:
    print(f"TCP connection failed: {e}")
