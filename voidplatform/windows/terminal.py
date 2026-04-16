"""Windows terminal management via subprocess pipes.

Windows does not have pty.fork(). On Windows, we use subprocess.Popen
with piped stdin/stdout to provide interactive shell access.
For full VT/ANSI support, ConPTY could be used via the winpty package.
"""
import os
import subprocess
import sys
from ..base import TerminalManager


class WindowsTerminalManager(TerminalManager):
    def is_available(self):
        # PowerShell/cmd is always available on Windows
        return sys.platform == 'win32'

    def spawn_shell(self, user=''):
        """Spawn a shell process.

        Returns (process_obj, process_obj) since Windows doesn't use fd-based I/O.
        The caller uses proc.stdin / proc.stdout / proc.stderr for communication.
        """
        if not self.is_available():
            raise RuntimeError('Windows terminal not available on this platform')

        shell = os.environ.get('COMSPEC', 'cmd.exe')
        # Prefer PowerShell if available
        ps = r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
        if os.path.exists(ps):
            shell = ps

        proc = subprocess.Popen(
            [shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            bufsize=0,
        )
        # Return (proc, proc) to match the (pid, fd) tuple interface
        # The caller should check isinstance to determine I/O method
        return proc, proc

    def read(self, fd, size=8192):
        """Read from the process stdout.
        fd is the Popen object on Windows.
        """
        if hasattr(fd, 'stdout'):
            return fd.stdout.read1(size) if hasattr(fd.stdout, 'read1') else fd.stdout.read(size)
        return b''

    def write(self, fd, data):
        """Write to the process stdin."""
        if hasattr(fd, 'stdin') and fd.stdin:
            fd.stdin.write(data)
            fd.stdin.flush()

    def resize(self, fd, rows, cols):
        """Terminal resize — limited support on Windows cmd/PowerShell.
        ConPTY would be needed for proper resize support.
        """
        # Windows cmd/PowerShell doesn't support TIOCSWINSZ-style resize
        # This is a known limitation without ConPTY
        pass

    def kill(self, pid):
        """Terminate a process. pid is the Popen object on Windows."""
        try:
            if hasattr(pid, 'terminate'):
                pid.terminate()
                pid.wait(timeout=5)
            elif isinstance(pid, int):
                subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                               capture_output=True, timeout=10)
        except Exception:
            pass
