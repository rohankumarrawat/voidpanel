#!/usr/bin/env python3
"""
SecureMailScope — AI Posture Scorer & Anomaly Detector
Calculates NIST-aligned 0-100 Cryptographic Health Score, detects anomalous TLS
fingerprints via Isolation Forest machine learning, and produces prioritized remediation advice.
"""

from typing import Dict, Any, List
import numpy as np
from sklearn.ensemble import IsolationForest


class AiPostureScorer:
    """Evaluates security posture, calculates health scores, and flags anomalies using ML."""

    def __init__(self):
        # Initialize an Isolation Forest for anomaly detection
        self.anomaly_detector = IsolationForest(
            n_estimators=100,
            contamination=0.15,
            random_state=42
        )
        self._fit_baseline_model()

    def _fit_baseline_model(self):
        """Pre-trains model on normal, compliant enterprise email traffic patterns."""
        # Feature vector: [tls_ver_code, cipher_count, pfs_int, is_implicit, cert_valid, key_size, stripped_int, leak_int]
        # Normal baseline samples (TLS 1.2/1.3, PFS=1, Valid Cert, KeySize >= 2048, Stripped=0, Leak=0)
        normal_samples = np.array([
            [0x0304, 5, 1, 1, 1, 2048, 0, 0],
            [0x0304, 6, 1, 0, 1, 256, 0, 0],
            [0x0303, 12, 1, 1, 1, 4096, 0, 0],
            [0x0303, 10, 1, 0, 1, 2048, 0, 0],
            [0x0304, 4, 1, 1, 1, 2048, 0, 0],
            [0x0303, 15, 1, 1, 1, 2048, 0, 0],
            [0x0304, 7, 1, 0, 1, 256, 0, 0],
            [0x0303, 8, 1, 1, 1, 2048, 0, 0],
        ])
        self.anomaly_detector.fit(normal_samples)

    def evaluate_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates security deductions, detects anomalies, and generates prioritized findings."""
        score = 100
        findings = []
        recommendations = []

        sh = session.get("tls_server_hello")
        ch = session.get("tls_client_hello")
        certs = session.get("certificates", [])

        # 1. Plaintext & STARTTLS Stripping Check (CRITICAL)
        if session.get("is_starttls_stripped"):
            deduction = 45
            score -= deduction
            findings.append({
                "severity": "CRITICAL",
                "category": "STARTTLS_STRIPPING",
                "title": "STARTTLS Stripping / Cleartext Exposure Detected",
                "detail": f"Connection on {session.get('protocol')} transmitted unencrypted message/credentials across the wire without TLS.",
                "deduction": deduction,
            })
            recommendations.append(
                "Enforce strict TLS on the mail server. In Postfix: set `smtp_tls_security_level = dane` or `enforce` to prevent plaintext fallbacks."
            )
        elif session.get("plaintext_leak_detected") and not sh:
            deduction = 40
            score -= deduction
            findings.append({
                "severity": "CRITICAL",
                "category": "PLAINTEXT_TRANSMISSION",
                "title": "Unencrypted Email Transmission",
                "detail": "Sensitive email headers or authentication commands were observed in cleartext.",
                "deduction": deduction,
            })

        # 2. TLS Version Assessment
        if sh:
            ver = sh.get("negotiated_version")
            if ver in (0x0300, 0x0301):  # SSL 3.0 or TLS 1.0
                deduction = 30
                score -= deduction
                findings.append({
                    "severity": "CRITICAL",
                    "category": "DEPRECATED_PROTOCOL",
                    "title": f"Banned TLS Version in Use: {sh.get('negotiated_version_name')}",
                    "detail": "TLS 1.0/SSL 3.0 was deprecated by RFC 8996 and is vulnerable to BEAST, POODLE, and downgrade exploits.",
                    "deduction": deduction,
                })
                recommendations.append("Disable TLS 1.0 and 1.1. In Postfix set `smtpd_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1`.")
            elif ver == 0x0302:  # TLS 1.1
                deduction = 20
                score -= deduction
                findings.append({
                    "severity": "HIGH",
                    "category": "DEPRECATED_PROTOCOL",
                    "title": "Deprecated TLS 1.1 Protocol",
                    "detail": "TLS 1.1 lacks modern cipher support and is retired from enterprise standards.",
                    "deduction": deduction,
                })
            elif ver == 0x0304:  # TLS 1.3
                findings.append({
                    "severity": "INFO",
                    "category": "MODERN_PROTOCOL",
                    "title": "State-of-the-Art TLS 1.3 Negotiated",
                    "detail": "Session utilizes modern 1-RTT encrypted handshake with mandated Forward Secrecy.",
                    "deduction": 0,
                })

            # 3. Cipher Suite & Forward Secrecy (PFS)
            pfs = sh.get("has_forward_secrecy", False)
            if not pfs:
                deduction = 15
                score -= deduction
                findings.append({
                    "severity": "MEDIUM",
                    "category": "NO_FORWARD_SECRECY",
                    "title": f"Lack of Perfect Forward Secrecy (PFS): {sh.get('cipher_name')}",
                    "detail": "Negotiated cipher uses static RSA key exchange. If server private key is compromised in the future, past recorded sessions can be decrypted.",
                    "deduction": deduction,
                })
                recommendations.append("Configure ECDHE cipher suites (e.g. `ECDHE-ECDSA-AES256-GCM-SHA384` or `ECDHE-RSA-AES256-GCM-SHA384`).")

            if "3DES" in sh.get("cipher_name", "") or "RC4" in sh.get("cipher_name", ""):
                deduction = 25
                score -= deduction
                findings.append({
                    "severity": "CRITICAL",
                    "category": "WEAK_CIPHER",
                    "title": f"Insecure Legacy Cipher: {sh.get('cipher_name')}",
                    "detail": "3DES/RC4 ciphers suffer from 64-bit block collisions (SWEET32) and statistical stream biases.",
                    "deduction": deduction,
                })

        # 4. X.509 Certificate Validation
        for cert in certs:
            if cert.get("is_expired"):
                deduction = 25
                score -= deduction
                findings.append({
                    "severity": "HIGH",
                    "category": "EXPIRED_CERTIFICATE",
                    "title": f"Expired Digital Certificate: {cert.get('subject')}",
                    "detail": f"Certificate expired on {cert.get('valid_until')}. Vulnerable to Man-in-the-Middle impersonation.",
                    "deduction": deduction,
                })
                recommendations.append("Renew certificate immediately using Certbot / Let's Encrypt or corporate PKI.")

            if cert.get("is_self_signed"):
                deduction = 15
                score -= deduction
                findings.append({
                    "severity": "MEDIUM",
                    "category": "SELF_SIGNED_CERTIFICATE",
                    "title": f"Self-Signed Certificate in Production: {cert.get('subject')}",
                    "detail": "Untrusted self-signed certificate cannot be verified against standard root CA stores.",
                    "deduction": deduction,
                })

            if cert.get("is_weak_key"):
                deduction = 20
                score -= deduction
                findings.append({
                    "severity": "HIGH",
                    "category": "WEAK_PUBLIC_KEY",
                    "title": f"Weak RSA Key Length ({cert.get('key_size_bits')} bits)",
                    "detail": "RSA keys smaller than 2048 bits are vulnerable to factorization attacks.",
                    "deduction": deduction,
                })

        # Bound score between 0 and 100
        final_score = max(0, min(100, score))

        # Assign Grade
        if final_score >= 95:
            grade = "A+"
        elif final_score >= 85:
            grade = "A"
        elif final_score >= 70:
            grade = "B"
        elif final_score >= 50:
            grade = "C"
        else:
            grade = "F (CRITICAL RISK)"

        # 5. ML Anomaly Detection Feature Extraction
        tls_ver_code = sh.get("negotiated_version", 0) if sh else 0
        cipher_count = ch.get("cipher_count", 0) if ch else 0
        pfs_int = 1 if (sh and sh.get("has_forward_secrecy")) else 0
        is_implicit = 1 if session.get("is_implicit_tls") else 0
        cert_valid = 0 if any(c.get("is_expired") for c in certs) else 1
        key_size = certs[0].get("key_size_bits", 2048) if certs else 2048
        stripped_int = 1 if session.get("is_starttls_stripped") else 0
        leak_int = 1 if session.get("plaintext_leak_detected") else 0

        feature_vector = np.array([[tls_ver_code, cipher_count, pfs_int, is_implicit, cert_valid, key_size, stripped_int, leak_int]])
        ml_prediction = self.anomaly_detector.predict(feature_vector)[0]
        anomaly_score_raw = self.anomaly_detector.decision_function(feature_vector)[0]

        # Invert decision function: lower values mean more anomalous
        is_anomalous = bool(ml_prediction == -1 or stripped_int == 1 or tls_ver_code == 0x0301)
        anomaly_confidence = int(min(100, max(5, (0.5 - float(anomaly_score_raw)) * 100)))

        return {
            "session_id": str(session.get("session_id")),
            "protocol": str(session.get("protocol")),
            "health_score": int(final_score),
            "grade": str(grade),
            "findings_count": int(len(findings)),
            "findings": findings,
            "recommendations": list(set(recommendations)),
            "is_anomalous": is_anomalous,
            "anomaly_confidence_pct": anomaly_confidence if is_anomalous else 0,
            "ja3_hash": str(ch.get("ja3_hash")) if ch else "N/A",
            "tls_version": str(sh.get("negotiated_version_name")) if sh else ("Plaintext / None" if session.get("is_starttls_stripped") else "Unknown"),
            "cipher_name": str(sh.get("cipher_name")) if sh else "None",
            "has_forward_secrecy": bool(sh.get("has_forward_secrecy", False)) if sh else False,
        }
