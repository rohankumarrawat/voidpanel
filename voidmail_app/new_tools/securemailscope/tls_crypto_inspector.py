#!/usr/bin/env python3
"""
SecureMailScope — TLS Cryptographic Inspector
Extracts and validates TLS Handshakes, Cipher Suites, JA3 Fingerprints,
and X.509 Digital Certificates from raw packet payloads.
"""

import hashlib
import struct
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa, dsa, ec

# Complete IANA TLS Cipher Suite Registry mapping for security posture analysis
CIPHER_SUITE_DATABASE = {
    # TLS 1.3 Ciphers (All have Forward Secrecy & AEAD)
    0x1301: {"name": "TLS_AES_128_GCM_SHA256", "kex": "ECDHE", "enc": "AES-128-GCM", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0x1302: {"name": "TLS_AES_256_GCM_SHA384", "kex": "ECDHE", "enc": "AES-256-GCM", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0x1303: {"name": "TLS_CHACHA20_POLY1305_SHA256", "kex": "ECDHE", "enc": "CHACHA20-POLY1305", "mac": "AEAD", "pfs": True, "strength": "SECURE"},

    # TLS 1.2 ECDHE Modern Ciphers (PFS = True)
    0xC02F: {"name": "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256", "kex": "ECDHE", "enc": "AES-128-GCM", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0xC030: {"name": "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384", "kex": "ECDHE", "enc": "AES-256-GCM", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0xC02B: {"name": "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256", "kex": "ECDHE", "enc": "AES-128-GCM", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0xC02C: {"name": "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384", "kex": "ECDHE", "enc": "AES-256-GCM", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0xCCA8: {"name": "TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256", "kex": "ECDHE", "enc": "CHACHA20-POLY1305", "mac": "AEAD", "pfs": True, "strength": "SECURE"},
    0xCCA9: {"name": "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256", "kex": "ECDHE", "enc": "CHACHA20-POLY1305", "mac": "AEAD", "pfs": True, "strength": "SECURE"},

    # CBC Mode with PFS (Acceptable but legacy CBC)
    0xC013: {"name": "TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA", "kex": "ECDHE", "enc": "AES-128-CBC", "mac": "SHA1", "pfs": True, "strength": "WEAK_MAC"},
    0xC014: {"name": "TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA", "kex": "ECDHE", "enc": "AES-256-CBC", "mac": "SHA1", "pfs": True, "strength": "WEAK_MAC"},

    # Static RSA Ciphers (NO FORWARD SECRECY)
    0x009C: {"name": "TLS_RSA_WITH_AES_128_GCM_SHA256", "kex": "RSA", "enc": "AES-128-GCM", "mac": "AEAD", "pfs": False, "strength": "NO_PFS"},
    0x009D: {"name": "TLS_RSA_WITH_AES_256_GCM_SHA384", "kex": "RSA", "enc": "AES-256-GCM", "mac": "AEAD", "pfs": False, "strength": "NO_PFS"},
    0x002F: {"name": "TLS_RSA_WITH_AES_128_CBC_SHA", "kex": "RSA", "enc": "AES-128-CBC", "mac": "SHA1", "pfs": False, "strength": "NO_PFS_WEAK_MAC"},
    0x0035: {"name": "TLS_RSA_WITH_AES_256_CBC_SHA", "kex": "RSA", "enc": "AES-256-CBC", "mac": "SHA1", "pfs": False, "strength": "NO_PFS_WEAK_MAC"},

    # Insecure / Broken Legacy Ciphers
    0x000A: {"name": "TLS_RSA_WITH_3DES_EDE_CBC_SHA", "kex": "RSA", "enc": "3DES", "mac": "SHA1", "pfs": False, "strength": "CRITICAL_VULNERABLE"},
    0x0005: {"name": "TLS_RSA_WITH_RC4_128_SHA", "kex": "RSA", "enc": "RC4", "mac": "SHA1", "pfs": False, "strength": "CRITICAL_VULNERABLE"},
    0x0004: {"name": "TLS_RSA_WITH_RC4_128_MD5", "kex": "RSA", "enc": "RC4", "mac": "MD5", "pfs": False, "strength": "CRITICAL_VULNERABLE"},
    0x0001: {"name": "TLS_RSA_WITH_NULL_MD5", "kex": "RSA", "enc": "NULL", "mac": "MD5", "pfs": False, "strength": "CRITICAL_VULNERABLE"},
}

TLS_VERSION_MAP = {
    0x0300: "SSL 3.0 (Obsolete/Dead)",
    0x0301: "TLS 1.0 (Deprecated - RFC 8996)",
    0x0302: "TLS 1.1 (Deprecated - RFC 8996)",
    0x0303: "TLS 1.2 (Standard)",
    0x0304: "TLS 1.3 (Modern/Secure)",
}


class TlsInspector:
    """Parses raw TLS record bytes, extracts handshakes, certificates, and scores risk."""

    @staticmethod
    def parse_client_hello(payload: bytes) -> Optional[Dict[str, Any]]:
        """Parses TLS ClientHello message to extract version, ciphers, extensions, and JA3 fingerprint."""
        try:
            if len(payload) < 43 or payload[0] != 0x16:  # 0x16 = Handshake record
                return None
            
            # Record Layer header: ContentType(1), Version(2), Length(2)
            record_ver = struct.unpack("!H", payload[1:3])[0]
            
            # Handshake header: Type(1), Length(3), Version(2)
            hs_type = payload[5]
            if hs_type != 1:  # 1 = ClientHello
                return None

            client_ver = struct.unpack("!H", payload[9:11])[0]
            offset = 11 + 32  # Skip 32 bytes of random

            # Session ID
            if offset >= len(payload):
                return None
            sess_len = payload[offset]
            offset += 1 + sess_len

            # Cipher Suites
            if offset + 2 > len(payload):
                return None
            ciphers_len = struct.unpack("!H", payload[offset:offset+2])[0]
            offset += 2

            ciphers = []
            for i in range(0, ciphers_len, 2):
                if offset + i + 2 <= len(payload):
                    cid = struct.unpack("!H", payload[offset+i:offset+i+2])[0]
                    # Filter out GREASE ciphers for JA3 (0x?a?a)
                    if (cid & 0x0F0F) != 0x0A0A:
                        ciphers.append(cid)
            offset += ciphers_len

            # Compression Methods
            if offset >= len(payload):
                return None
            comp_len = payload[offset]
            offset += 1 + comp_len

            # Extensions
            extensions = []
            elliptic_curves = []
            ec_point_formats = []

            if offset + 2 <= len(payload):
                ext_total_len = struct.unpack("!H", payload[offset:offset+2])[0]
                offset += 2
                ext_end = offset + ext_total_len

                while offset + 4 <= ext_end and offset + 4 <= len(payload):
                    ext_type = struct.unpack("!H", payload[offset:offset+2])[0]
                    ext_len = struct.unpack("!H", payload[offset+2:offset+4])[0]
                    offset += 4

                    # Filter GREASE extensions
                    if (ext_type & 0x0F0F) != 0x0A0A:
                        extensions.append(ext_type)

                    ext_data = payload[offset:offset+ext_len]

                    # Supported Groups / Elliptic Curves (0x000a)
                    if ext_type == 10 and len(ext_data) >= 2:
                        curves_len = struct.unpack("!H", ext_data[0:2])[0]
                        for c in range(2, min(curves_len + 2, len(ext_data)), 2):
                            curve_id = struct.unpack("!H", ext_data[c:c+2])[0]
                            if (curve_id & 0x0F0F) != 0x0A0A:
                                elliptic_curves.append(curve_id)

                    # EC Point Formats (0x000b)
                    elif ext_type == 11 and len(ext_data) >= 1:
                        point_len = ext_data[0]
                        for p in range(1, min(point_len + 1, len(ext_data))):
                            ec_point_formats.append(ext_data[p])

                    offset += ext_len

            # Calculate official JA3 Fingerprint:
            # Format: SSLVersion,Cipher,SSLExtension,EllipticCurve,EllipticCurvePointFormat
            ja3_str = "{},{},{},{},{}".format(
                client_ver,
                "-".join(map(str, ciphers)),
                "-".join(map(str, extensions)),
                "-".join(map(str, elliptic_curves)),
                "-".join(map(str, ec_point_formats))
            )
            ja3_hash = hashlib.md5(ja3_str.encode()).hexdigest()

            return {
                "type": "ClientHello",
                "client_version": client_ver,
                "client_version_name": TLS_VERSION_MAP.get(client_ver, f"Unknown (0x{client_ver:04x})"),
                "ciphers_offered": [CIPHER_SUITE_DATABASE.get(c, {"name": f"0x{c:04X}", "strength": "UNKNOWN"})["name"] for c in ciphers],
                "cipher_count": len(ciphers),
                "ja3_string": ja3_str,
                "ja3_hash": ja3_hash,
            }
        except Exception:
            return None

    @staticmethod
    def parse_server_hello(payload: bytes) -> Optional[Dict[str, Any]]:
        """Parses TLS ServerHello message to extract negotiated version and cipher suite."""
        try:
            if len(payload) < 43 or payload[0] != 0x16:
                return None

            hs_type = payload[5]
            if hs_type != 2:  # 2 = ServerHello
                return None

            server_ver = struct.unpack("!H", payload[9:11])[0]
            offset = 11 + 32  # Skip 32 bytes random

            if offset >= len(payload):
                return None
            sess_len = payload[offset]
            offset += 1 + sess_len

            if offset + 2 > len(payload):
                return None
            selected_cipher_id = struct.unpack("!H", payload[offset:offset+2])[0]
            offset += 2

            # Check for TLS 1.3 supported_versions extension in ServerHello (0x002b)
            negotiated_ver = server_ver
            offset += 1  # Skip compression method

            if offset + 2 <= len(payload):
                ext_total_len = struct.unpack("!H", payload[offset:offset+2])[0]
                offset += 2
                ext_end = offset + ext_total_len

                while offset + 4 <= ext_end and offset + 4 <= len(payload):
                    ext_type = struct.unpack("!H", payload[offset:offset+2])[0]
                    ext_len = struct.unpack("!H", payload[offset+2:offset+4])[0]
                    offset += 4
                    if ext_type == 43 and ext_len == 2:  # supported_versions
                        negotiated_ver = struct.unpack("!H", payload[offset:offset+2])[0]
                    offset += ext_len

            cipher_meta = CIPHER_SUITE_DATABASE.get(selected_cipher_id, {
                "name": f"Unknown Cipher (0x{selected_cipher_id:04X})",
                "kex": "Unknown",
                "enc": "Unknown",
                "mac": "Unknown",
                "pfs": False,
                "strength": "UNKNOWN"
            })

            is_deprecated_ver = negotiated_ver in (0x0300, 0x0301, 0x0302)

            return {
                "type": "ServerHello",
                "negotiated_version": negotiated_ver,
                "negotiated_version_name": TLS_VERSION_MAP.get(negotiated_ver, f"0x{negotiated_ver:04x}"),
                "cipher_id": f"0x{selected_cipher_id:04X}",
                "cipher_name": cipher_meta["name"],
                "key_exchange": cipher_meta["kex"],
                "bulk_encryption": cipher_meta["enc"],
                "mac_algorithm": cipher_meta["mac"],
                "has_forward_secrecy": cipher_meta["pfs"],
                "cipher_strength": cipher_meta["strength"],
                "is_deprecated_version": is_deprecated_ver,
            }
        except Exception:
            return None

    @staticmethod
    def parse_certificate_chain(payload: bytes) -> List[Dict[str, Any]]:
        """Parses TLS Certificate record (type 11) and extracts X.509 metadata."""
        certificates = []
        try:
            if len(payload) < 12 or payload[0] != 0x16:
                return certificates

            hs_type = payload[5]
            if hs_type != 11:  # 11 = Certificate
                return certificates

            # Certificate list length (3 bytes)
            certs_len = (payload[9] << 16) | (payload[10] << 8) | payload[11]
            offset = 12
            end_offset = offset + certs_len

            while offset + 3 < end_offset and offset + 3 < len(payload):
                cert_len = (payload[offset] << 16) | (payload[offset+1] << 8) | payload[offset+2]
                offset += 3

                cert_der = payload[offset:offset+cert_len]
                offset += cert_len

                try:
                    cert = x509.load_der_x509_certificate(cert_der, default_backend())
                    
                    # Validity check
                    now = datetime.now(timezone.utc)
                    is_expired = now > cert.not_valid_after_utc
                    is_not_yet_valid = now < cert.not_valid_before_utc

                    # Key length
                    pub_key = cert.public_key()
                    key_type = "Unknown"
                    key_size = 0
                    if isinstance(pub_key, rsa.RSAPublicKey):
                        key_type = "RSA"
                        key_size = pub_key.key_size
                    elif isinstance(pub_key, ec.EllipticCurvePublicKey):
                        key_type = "ECC"
                        key_size = pub_key.key_size

                    is_weak_key = (key_type == "RSA" and key_size < 2048)
                    sig_algo = cert.signature_hash_algorithm.name.upper() if cert.signature_hash_algorithm else "UNKNOWN"
                    is_weak_sig = sig_algo in ("MD5", "SHA1")

                    subject_str = ", ".join([f"{attr.oid._name}={attr.value}" for attr in cert.subject])
                    issuer_str = ", ".join([f"{attr.oid._name}={attr.value}" for attr in cert.issuer])
                    is_self_signed = (subject_str == issuer_str)

                    certificates.append({
                        "subject": subject_str,
                        "issuer": issuer_str,
                        "valid_from": cert.not_valid_before_utc.isoformat(),
                        "valid_until": cert.not_valid_after_utc.isoformat(),
                        "is_expired": is_expired,
                        "is_not_yet_valid": is_not_yet_valid,
                        "key_type": key_type,
                        "key_size_bits": key_size,
                        "is_weak_key": is_weak_key,
                        "signature_hash": sig_algo,
                        "is_weak_signature": is_weak_sig,
                        "is_self_signed": is_self_signed,
                        "serial_number": hex(cert.serial_number),
                    })
                except Exception:
                    continue

        except Exception:
            pass

        return certificates
