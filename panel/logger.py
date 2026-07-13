"""
VoidPanel structured logging configuration.
All panel functions should use this instead of open('/var/logs.txt', 'a').

Usage:
    from panel.logger import get_logger
    logger = get_logger(__name__)
    logger.info("User %s provisioned", username)
    logger.error("Provisioning failed for %s: %s", domain, err)
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path


def _resolve_log_dir() -> str:
    """
    Resolve the log directory for this environment.

    - Linux / WSL2 running as root   →  /var/log/voidpanel  (production path)
    - macOS, native Windows, or any  →  <project_root>/logs/ (dev fallback)
      Linux without write access to
      /var/log/

    Catches both PermissionError and the broader OSError so that any
    platform-specific failure (e.g. Windows interpreting the path as a
    Windows drive path) falls back cleanly instead of crashing Django startup.
    """
    fallback = str(Path(__file__).resolve().parent.parent / 'logs')

    # On native Windows the POSIX path /var/log/voidpanel is meaningless.
    # Skip it entirely to avoid accidentally creating C:\var\log\voidpanel.
    if sys.platform == 'win32':
        return fallback

    primary = '/var/log/voidpanel'
    try:
        os.makedirs(primary, exist_ok=True)
        return primary
    except (PermissionError, OSError):
        # Local development, macOS, or Linux without /var/log write access.
        return fallback


LOG_DIR   = _resolve_log_dir()
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE  = os.path.join(LOG_DIR, 'panel.log')
ERROR_LOG = os.path.join(LOG_DIR, 'error.log')


def _build_handler(path: str, level: int) -> logging.Handler:
    """Rotating file handler — max 10 MB, keep 5 backups."""
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
    )
    handler.setLevel(level)
    handler.setFormatter(_fmt())
    return handler


def _fmt() -> logging.Formatter:
    return logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )


def _configure_root() -> None:
    root = logging.getLogger('voidpanel')
    if root.handlers:          # already configured — skip
        return
    root.setLevel(logging.DEBUG)

    # All logs → panel.log
    try:
        root.addHandler(_build_handler(LOG_FILE, logging.DEBUG))
    except (PermissionError, OSError):
        pass  # Running locally without write access to log dir

    # Errors only → error.log
    try:
        root.addHandler(_build_handler(ERROR_LOG, logging.ERROR))
    except (PermissionError, OSError):
        pass

    # Console (only if DEBUG env is set)
    if os.environ.get('VOIDPANEL_DEBUG'):
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(_fmt())
        root.addHandler(console)

    root.propagate = False


_configure_root()


def get_logger(name: str) -> logging.Logger:
    """
    Return a named child of the 'voidpanel' root logger.

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        logging.Logger ready to use.
    """
    return logging.getLogger(f'voidpanel.{name}')
