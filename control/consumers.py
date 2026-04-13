import os
import sys
import struct
import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

# pty, fcntl, and termios are POSIX-only (Linux/macOS/WSL2).
# On native Windows these modules do not exist, causing a ModuleNotFoundError
# at import time that crashes Django startup entirely.
# Guard them so the panel can at least start on Windows (e.g. for UI dev).
# In production, VoidPanel runs inside WSL2 Ubuntu where these work normally.
_POSIX_PTY = False
try:
    import pty
    import fcntl
    import termios
    _POSIX_PTY = True
except ImportError:
    pass  # Native Windows — terminal WebSocket will send an informative error

class TerminalConsumer(AsyncWebsocketConsumer):
    
    @database_sync_to_async
    def check_shell_access(self, username):
        from control.models import user as control_user
        try:
            usr = control_user.objects.get(username=username)
            return getattr(usr, 'shell', False)
        except Exception:
            return False

    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        # On native Windows, pty is unavailable. WSL2 is the supported path.
        if not _POSIX_PTY:
            await self.accept()
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': (
                    'The web terminal requires a POSIX environment (Linux / WSL2). '
                    'On Windows, run VoidPanel inside WSL2 (Ubuntu-22.04) where this '
                    'feature works exactly as on Linux. '
                    'Start WSL2 shell: wsl -d Ubuntu-22.04'
                )
            }))
            await self.close()
            return

        # Dynamic Masking: Determine target sandbox directory map
        if self.user.is_superuser:
            session_name = self.scope.get("session", {}).get("name")
            self.target_user = session_name if session_name else "root"
        else:
            self.target_user = self.user.username
            
        # Explicit Shell Evaluation Boundary
        if self.target_user != "root":
            has_shell = await self.check_shell_access(self.target_user)
            if not has_shell:
                await self.close()
                return

        await self.accept()

        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            # Fork Payload
            if self.target_user == "root":
                os.execvp("bash", ["bash", "-l"])
            else:
                # Industry standard Jailed sandbox via `su -` drops privileges natively 
                # resolving ~ paths and triggering local unprivileged .bash_profile
                os.execvp("su", ["su", "-", self.target_user])
            
        self.loop = asyncio.get_event_loop()
        self.loop.add_reader(self.fd, self._read_pty)

    def _read_pty(self):
        try:
            data = os.read(self.fd, 8192)
            if data:
                asyncio.ensure_future(self.send(text_data=data.decode('utf-8', 'replace')))
            else:
                asyncio.ensure_future(self.close())
        except OSError:
            asyncio.ensure_future(self.close())

    async def disconnect(self, close_code):
        if hasattr(self, 'fd'):
            try:
                self.loop.remove_reader(self.fd)
                os.close(self.fd)
            except Exception:
                pass
        
        if hasattr(self, 'pid'):
            try:
                import signal
                os.kill(self.pid, signal.SIGKILL)
                os.waitpid(self.pid, 0)
            except Exception:
                pass

    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                msg = json.loads(text_data)
                if msg.get('action') == 'resize':
                    rows = msg.get("rows", 24)
                    cols = msg.get("cols", 80)
                    winsize = struct.pack("HHHH", rows, cols, 0, 0)
                    if _POSIX_PTY and hasattr(self, 'fd'):
                        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
                elif msg.get('action') == 'input':
                    data = msg.get('data', '')
                    os.write(self.fd, data.encode('utf-8'))
            except Exception:
                pass
