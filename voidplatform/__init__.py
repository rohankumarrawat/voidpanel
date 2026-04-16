"""VoidPanel cross-platform abstraction layer.

Usage:
    from platform import get_platform
    p = get_platform()
    p.services.restart('nginx')
    p.users.create_user('alice', 'secret')
    p.web.create_site('example.com', '/home/alice/public_html')
    p.dns.create_zone('example.com', '1.2.3.4')
    p.mail.create_account('info@example.com', 'secret')
"""
from .detector import detect, Environment, is_windows, is_linux, is_wsl2
from .base import Platform

_instance = None


def get_platform():
    """Return the platform singleton for the current OS."""
    global _instance
    if _instance is not None:
        return _instance

    env = detect()
    if env in (Environment.LINUX, Environment.WSL2):
        from .linux import LinuxPlatform
        _instance = LinuxPlatform()
    elif env == Environment.WINDOWS:
        from .windows import WindowsPlatform
        _instance = WindowsPlatform()
    else:
        raise RuntimeError(
            f"VoidPanel does not support this platform: {env.value}. "
            "Supported: Linux (Ubuntu 22.04+), Windows 10/11, WSL2."
        )
    return _instance
