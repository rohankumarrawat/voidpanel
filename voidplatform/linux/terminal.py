"""Linux PTY terminal management."""
import os
from ..base import TerminalManager

_POSIX_PTY = False
try:
    import pty
    import fcntl
    import termios
    import struct
    import signal
    _POSIX_PTY = True
except ImportError:
    pass


class LinuxTerminalManager(TerminalManager):
    def is_available(self):
        return _POSIX_PTY

    def spawn_shell(self, user=''):
        if not _POSIX_PTY:
            raise RuntimeError('PTY not available on this platform')
        pid, fd = pty.fork()
        if pid == 0:
            try:
                import resource
                max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
                if max_fd == resource.RLIM_INFINITY:
                    max_fd = 1024
            except Exception:
                max_fd = 1024
            os.closerange(3, max_fd)

            if user and user != 'root':
                os.execvp('su', ['su', '-', user])
            else:
                os.execvp('bash', ['bash', '-l'])
        return pid, fd

    def read(self, fd, size=8192):
        return os.read(fd, size)

    def write(self, fd, data):
        os.write(fd, data)

    def resize(self, fd, rows, cols):
        if _POSIX_PTY:
            winsize = struct.pack('HHHH', rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

    def kill(self, pid):
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except Exception:
            pass
