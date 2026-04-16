"""OS / environment detection for VoidPanel."""
import sys
from enum import Enum


class Environment(Enum):
    LINUX = "linux"
    WSL2 = "wsl2"
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"


_cached = None


def detect():
    global _cached
    if _cached is not None:
        return _cached

    if sys.platform == 'win32':
        _cached = Environment.WINDOWS
    elif sys.platform == 'darwin':
        _cached = Environment.MACOS
    elif sys.platform.startswith('linux'):
        try:
            with open('/proc/version', 'r') as f:
                ver = f.read().lower()
            if 'microsoft' in ver or 'wsl' in ver:
                _cached = Environment.WSL2
            else:
                _cached = Environment.LINUX
        except (FileNotFoundError, PermissionError):
            _cached = Environment.LINUX
    else:
        _cached = Environment.UNKNOWN
    return _cached


def is_windows():
    return detect() == Environment.WINDOWS


def is_linux():
    return detect() in (Environment.LINUX, Environment.WSL2)


def is_wsl2():
    return detect() == Environment.WSL2
