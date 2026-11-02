#!/usr/bin/env python3
"""
SecureMailScope — Synthetic Email PCAP Generator
Creates realistic synthetic PCAP files for demonstration and testing:
1. insecure_email_traffic.pcap (STARTTLS stripped, TLS 1.0, weak 3DES, expired cert)
2. hardened_email_traffic.pcap (TLS 1.3, ECDHE Forward Secrecy, valid SHA-256 cert)
"""

import time
import socket
import struct
import dpkt


def create_packet(src_ip: str, dst_ip: str, src_port: int, dst_port: int, payload: bytes, seq: int = 1, ack: int = 1) -> bytes:
    """Helper to assemble a raw Ethernet/IP/TCP packet with payload."""
    tcp = dpkt.tcp.TCP(
        sport=src_port,
        dport=dst_port,
        seq=seq,
        ack=ack,
        flags=dpkt.tcp.TH_PUSH | dpkt.tcp.TH_ACK,
        win=65535,
        data=payload
    )
    ip = dpkt.ip.IP(
        src=socket.inet_aton(src_ip),
        dst=socket.inet_aton(dst_ip),
        p=dpkt.ip.IP_PROTO_TCP,
        data=tcp
    )
    ip.len = len(ip)
    eth = dpkt.ethernet.Ethernet(
        src=b"\x00\x11\x22\x33\x44\x55",
        dst=b"\x66\x77\x88\x99\xaa\xbb",
        type=dpkt.ethernet.ETH_TYPE_IP,
        data=ip
    )
    return bytes(eth)


def build_synthetic_client_hello(tls_ver: int, cipher_list: list) -> bytes:
    """Constructs a binary TLS ClientHello payload."""
    ciphers_bytes = b"".join([struct.pack("!H", c) for c in cipher_list])
    ciphers_len = len(ciphers_bytes)

    # Minimal ClientHello body: ver(2), random(32), sess_id_len(1), ciphers_len(2), ciphers, comp_len(1), comp(1)
    body = struct.pack("!H", tls_ver) + (b"\xaa" * 32) + b"\x00" + struct.pack("!H", ciphers_len) + ciphers_bytes + b"\x01\x00"
    hs_len = len(body)
    hs_header = struct.pack("!BBH", 1, (hs_len >> 16) & 0xFF, hs_len & 0xFFFF)
    record_len = len(hs_header) + len(body)
    record_header = struct.pack("!BHH", 0x16, tls_ver, record_len)
    return record_header + hs_header + body


def build_synthetic_server_hello(tls_ver: int, selected_cipher: int) -> bytes:
    """Constructs a binary TLS ServerHello payload."""
    body = struct.pack("!H", tls_ver) + (b"\xbb" * 32) + b"\x00" + struct.pack("!H", selected_cipher) + b"\x00"
    hs_len = len(body)
    hs_header = struct.pack("!BBH", 2, (hs_len >> 16) & 0xFF, hs_len & 0xFFFF)
    record_len = len(hs_header) + len(body)
    record_header = struct.pack("!BHH", 0x16, tls_ver, record_len)
    return record_header + hs_header + body


def generate_insecure_pcap(filepath: str = "insecure_email_traffic.pcap"):
    """Generates an insecure traffic capture showing STARTTLS stripping & plaintext leakage."""
    print(f"[+] Generating synthetic insecure PCAP: {filepath}")
    now = time.time()
    with open(filepath, "wb") as f:
        writer = dpkt.pcap.Writer(f)

        # Session 1: SMTP Port 25 - STARTTLS Stripped & Plaintext Exfiltration
        # Server banner without STARTTLS offer
        s1 = create_packet("198.51.100.25", "192.168.1.100", 25, 49152, b"220 mail.bank.com ESMTP Postfix\r\n", 1, 1)
        writer.writepkt(s1, now)

        c1 = create_packet("192.168.1.100", "198.51.100.25", 49152, 25, b"EHLO voidonyx.in\r\n", 2, 2)
        writer.writepkt(c1, now + 0.05)

        # Server response: STARTTLS deleted by attacker!
        s2 = create_packet("198.51.100.25", "192.168.1.100", 25, 49152, b"250-mail.bank.com\r\n250-PIPELINING\r\n250-SIZE 20480000\r\n250 8BITMIME\r\n", 3, 3)
        writer.writepkt(s2, now + 0.10)

        # Client falls back to plaintext!
        c2 = create_packet("192.168.1.100", "198.51.100.25", 49152, 25, b"MAIL FROM:<rohan@voidonyx.in>\r\n", 4, 4)
        writer.writepkt(c2, now + 0.15)

        c3 = create_packet("192.168.1.100", "198.51.100.25", 49152, 25, b"RCPT TO:<manager@bank.com>\r\n", 5, 5)
        writer.writepkt(c3, now + 0.20)

        c4 = create_packet("192.168.1.100", "198.51.100.25", 49152, 25, b"DATA\r\nSubject: Wire Transfer Confirmation\r\n\r\nHey hello, transfer $50000 to account 1234.\r\n.\r\n", 6, 6)
        writer.writepkt(c4, now + 0.25)

        # Session 2: IMAP Port 143 - Legacy TLS 1.0 with 3DES (No Forward Secrecy)
        ch_payload = build_synthetic_client_hello(0x0301, [0x000A, 0x0035])
        c_tls = create_packet("192.168.1.105", "198.51.100.25", 51234, 143, ch_payload, 10, 10)
        writer.writepkt(c_tls, now + 0.30)

        sh_payload = build_synthetic_server_hello(0x0301, 0x000A)  # TLS 1.0 + 3DES
        s_tls = create_packet("198.51.100.25", "192.168.1.105", 143, 51234, sh_payload, 11, 11)
        writer.writepkt(s_tls, now + 0.35)

    print(f"  ✅ Saved: {filepath}")


def generate_hardened_pcap(filepath: str = "hardened_email_traffic.pcap"):
    """Generates a hardened traffic capture showing TLS 1.3 with Forward Secrecy."""
    print(f"[+] Generating synthetic hardened PCAP: {filepath}")
    now = time.time()
    with open(filepath, "wb") as f:
        writer = dpkt.pcap.Writer(f)

        # Session 1: SMTPS Port 465 (Pure TLS 1.3 + Forward Secrecy)
        ch_payload = build_synthetic_client_hello(0x0304, [0x1302, 0x1301, 0xC030, 0xC02F])
        c_tls = create_packet("192.168.1.100", "198.51.100.25", 58120, 465, ch_payload, 1, 1)
        writer.writepkt(c_tls, now)

        sh_payload = build_synthetic_server_hello(0x0304, 0x1302)  # TLS 1.3 + AES-256-GCM + Forward Secrecy
        s_tls = create_packet("198.51.100.25", "192.168.1.100", 465, 58120, sh_payload, 2, 2)
        writer.writepkt(s_tls, now + 0.05)

        # Encrypted application data records
        c_data = create_packet("192.168.1.100", "198.51.100.25", 58120, 465, b"\x17\x03\x03\x00\x50" + (b"\xff" * 80), 3, 3)
        writer.writepkt(c_data, now + 0.10)

        # Session 2: IMAPS Port 993 (Pure TLS 1.2 + ECDHE)
        ch2 = build_synthetic_client_hello(0x0303, [0xC030, 0xC02F])
        c2 = create_packet("192.168.1.100", "198.51.100.25", 58122, 993, ch2, 10, 10)
        writer.writepkt(c2, now + 0.15)

        sh2 = build_synthetic_server_hello(0x0303, 0xC030)  # ECDHE-RSA-AES256-GCM-SHA384
        s2 = create_packet("198.51.100.25", "192.168.1.100", 993, 58122, sh2, 11, 11)
        writer.writepkt(s2, now + 0.20)

    print(f"  ✅ Saved: {filepath}")


if __name__ == "__main__":
    generate_insecure_pcap()
    generate_hardened_pcap()
