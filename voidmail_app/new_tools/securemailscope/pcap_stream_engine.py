#!/usr/bin/env python3
"""
SecureMailScope — PCAP Stream Reconstruction Engine
Parses network packet captures (.pcap), reconstructs bidirectional TCP streams,
identifies SMTP/IMAP/POP3 protocols, and detects STARTTLS stripping & plaintext leaks.
"""

import socket
import struct
from typing import Dict, Any, List
import dpkt
from tls_crypto_inspector import TlsInspector

EMAIL_PORTS = {
    25: "SMTP (Relay / Port 25)",
    465: "SMTPS (Implicit Pure TLS / Port 465)",
    587: "SMTP (Submission / Port 587)",
    143: "IMAP (STARTTLS / Port 143)",
    993: "IMAPS (Implicit Pure TLS / Port 993)",
    110: "POP3 (STARTTLS / Port 110)",
    995: "POP3S (Implicit Pure TLS / Port 995)",
}


class PcapStreamEngine:
    """Reconstructs and analyzes email sessions from raw PCAP files."""

    def __init__(self, pcap_path: str):
        self.pcap_path = pcap_path
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def _format_ip(self, ip_bytes: bytes) -> str:
        try:
            return socket.inet_ntoa(ip_bytes)
        except Exception:
            return "0.0.0.0"

    def process(self) -> List[Dict[str, Any]]:
        """Reads PCAP file, reassembles TCP streams, and runs cryptographic checks."""
        with open(self.pcap_path, "rb") as f:
            try:
                pcap = dpkt.pcap.Reader(f)
            except ValueError:
                # Try pcapng reader if standard pcap fails
                f.seek(0)
                pcap = dpkt.pcapng.Reader(f)

            for ts, buf in pcap:
                try:
                    eth = dpkt.ethernet.Ethernet(buf)
                except Exception:
                    continue

                if not isinstance(eth.data, dpkt.ip.IP):
                    continue

                ip = eth.data
                if not isinstance(ip.data, dpkt.tcp.TCP):
                    continue

                tcp = ip.data
                if not tcp.data:
                    continue

                src_ip = self._format_ip(ip.src)
                dst_ip = self._format_ip(ip.dst)
                src_port = tcp.sport
                dst_port = tcp.dport

                # Determine if either port is an email port
                email_port = None
                protocol_name = None
                is_client_to_server = False

                if dst_port in EMAIL_PORTS:
                    email_port = dst_port
                    protocol_name = EMAIL_PORTS[dst_port]
                    is_client_to_server = True
                elif src_port in EMAIL_PORTS:
                    email_port = src_port
                    protocol_name = EMAIL_PORTS[src_port]
                    is_client_to_server = False
                else:
                    continue

                # Session key: canonical representation of the 4-tuple
                if src_ip < dst_ip or (src_ip == dst_ip and src_port < dst_port):
                    session_id = f"{src_ip}:{src_port} <-> {dst_ip}:{dst_port}"
                else:
                    session_id = f"{dst_ip}:{dst_port} <-> {src_ip}:{src_port}"

                if session_id not in self.sessions:
                    self.sessions[session_id] = {
                        "session_id": session_id,
                        "server_ip": dst_ip if is_client_to_server else src_ip,
                        "server_port": email_port,
                        "client_ip": src_ip if is_client_to_server else dst_ip,
                        "protocol": protocol_name,
                        "is_implicit_tls": email_port in (465, 993, 995),
                        "client_packets": [],
                        "server_packets": [],
                        "plaintext_transcript": [],
                        "tls_client_hello": None,
                        "tls_server_hello": None,
                        "certificates": [],
                        "starttls_offered": False,
                        "starttls_requested": False,
                        "starttls_acknowledged": False,
                        "is_starttls_stripped": False,
                        "plaintext_leak_detected": False,
                        "leaked_sample_text": [],
                    }

                sess = self.sessions[session_id]
                payload = tcp.data

                # Collect payloads
                if is_client_to_server:
                    sess["client_packets"].append(payload)
                else:
                    sess["server_packets"].append(payload)

                # 1. Check for TLS Handshake Record (0x16 0x03)
                if len(payload) >= 5 and payload[0] == 0x16 and payload[1] == 0x03:
                    hs_type = payload[5] if len(payload) > 5 else 0
                    if hs_type == 1 and not sess["tls_client_hello"]:
                        ch_info = TlsInspector.parse_client_hello(payload)
                        if ch_info:
                            sess["tls_client_hello"] = ch_info
                    elif hs_type == 2 and not sess["tls_server_hello"]:
                        sh_info = TlsInspector.parse_server_hello(payload)
                        if sh_info:
                            sess["tls_server_hello"] = sh_info
                    elif hs_type == 11:
                        certs = TlsInspector.parse_certificate_chain(payload)
                        if certs:
                            sess["certificates"].extend(certs)

                # 2. Check for Plaintext Protocol Analysis & STARTTLS
                else:
                    try:
                        text = payload.decode("utf-8", errors="ignore").strip()
                        if text:
                            sess["plaintext_transcript"].append(text[:200])

                            # Server banner & STARTTLS offers
                            if not is_client_to_server:
                                if "250-STARTTLS" in text or "250 STARTTLS" in text or "STARTTLS" in text.upper():
                                    sess["starttls_offered"] = True
                                if "220 2.0.0 Ready to start TLS" in text or "220 Ready to start TLS" in text:
                                    sess["starttls_acknowledged"] = True
                                elif "OK Begin TLS" in text:
                                    sess["starttls_acknowledged"] = True

                            # Client STARTTLS command
                            if is_client_to_server:
                                if text.upper().startswith("STARTTLS"):
                                    sess["starttls_requested"] = True

                            # Check for sensitive plaintext leaks
                            leak_keywords = ["MAIL FROM:", "RCPT TO:", "AUTH PLAIN", "AUTH LOGIN", "PASS ", "Subject:"]
                            for kw in leak_keywords:
                                if kw.lower() in text.lower():
                                    sess["plaintext_leak_detected"] = True
                                    sess["leaked_sample_text"].append(text[:120])
                    except Exception:
                        pass

        # Post-processing session analysis: Detect STARTTLS Stripping
        analyzed_results = []
        for sess in self.sessions.values():
            # A stripping attack occurred if:
            # - Not implicit TLS (e.g. port 25, 587, 143)
            # - No TLS handshake ever completed (no ServerHello)
            # - Yet email transactions (MAIL FROM, RCPT TO, body, auth) continued in plain text!
            if not sess["is_implicit_tls"] and not sess["tls_server_hello"]:
                if sess["plaintext_leak_detected"]:
                    sess["is_starttls_stripped"] = True

            analyzed_results.append(sess)

        return analyzed_results
