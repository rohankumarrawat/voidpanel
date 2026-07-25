"""
Symmetric encryption utilities for storing sensitive data (e.g. SaaS tenant passwords).

Uses Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library.
If `cryptography` is not installed, falls back to base64 encoding (NOT secure —
this is only so the app doesn't crash during development).

Set the FERNET_KEY environment variable to a valid Fernet key in production:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import base64
import os
import logging

logger = logging.getLogger(__name__)

_FERNET_KEY = os.environ.get('FERNET_KEY', '')

_fernet = None
try:
    from cryptography.fernet import Fernet, InvalidToken
    if _FERNET_KEY:
        _fernet = Fernet(_FERNET_KEY.encode())
    else:
        logger.warning(
            "FERNET_KEY env var not set — passwords will be base64-encoded only. "
            "Generate a key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
except ImportError:
    logger.warning(
        "cryptography library not installed. Install with: pip install cryptography"
    )
    InvalidToken = Exception  # dummy


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext password → storable string."""
    if not plaintext:
        return ''
    if _fernet:
        return _fernet.encrypt(plaintext.encode()).decode()
    # Fallback: base64 (NOT cryptographically secure, dev-only)
    return 'b64:' + base64.urlsafe_b64encode(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password → plaintext for provisioning API calls."""
    if not ciphertext:
        return ''
    # Already plaintext (legacy data before encryption was added)
    if not ciphertext.startswith('b64:') and not ciphertext.startswith('gAAAAA'):
        return ciphertext
    if ciphertext.startswith('b64:'):
        return base64.urlsafe_b64decode(ciphertext[4:]).decode()
    if _fernet:
        try:
            return _fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            logger.error("Failed to decrypt password — wrong FERNET_KEY?")
            return ''
    logger.error("Cannot decrypt Fernet ciphertext — cryptography not installed or FERNET_KEY not set")
    return ''
