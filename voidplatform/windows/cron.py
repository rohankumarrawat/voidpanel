"""
Windows Task Scheduler (schtasks.exe) — drop-in crontab replacement.

Converts cron expressions to schtasks /sc parameters and manages
VoidPanel scheduled tasks under the "VoidPanel\\" folder.
All VoidPanel tasks are named:  VoidPanel\vp_{hash}

API mirrors unix crontab semantics:
  list_crons()                    → list of (cron_expr, command) tuples
  add_cron(cron_expr, command)    → create schtask, return task_name
  delete_cron(command_substring)  → delete matching tasks
  crontab_minus(cron_text)        → bulk-load cron jobs (array of "expr cmd")
"""

import os
import re
import hashlib
import subprocess
import json

_TASK_FOLDER = "VoidPanel"
_REGISTRY    = None   # lazy-loaded JSON registry path

# ─────────────────────────────────────────────────────────────────────────────
# Registry helpers (persist cron_expr→task_name mapping in a JSON sidecar)
# ─────────────────────────────────────────────────────────────────────────────

def _reg_path():
    base = os.environ.get('VOIDPANEL_BASE', r'C:\VoidPanel')
    return os.path.join(base, 'cron_registry.json')


def _load_reg():
    p = _reg_path()
    if os.path.exists(p):
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_reg(reg):
    p = _reg_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        json.dump(reg, f, indent=2)


def _task_name(command):
    """Generate a stable task name from the command string."""
    h = hashlib.md5(command.encode()).hexdigest()[:8]
    return f"{_TASK_FOLDER}\\vp_{h}"


def _run(cmd, timeout=30):
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, '', str(e)


# ─────────────────────────────────────────────────────────────────────────────
# Cron → schtasks converter
# ─────────────────────────────────────────────────────────────────────────────

def _cron_to_schtasks(cron_expr):
    """
    Convert a 5-field cron expression to schtasks /sc + /mo + /st args.
    Returns a list of extra args to pass to schtasks /create.

    Supported patterns:
      * * * * *       → every 1 minute
      */N * * * *     → every N minutes
      0 * * * *       → hourly
      0 H * * *       → daily at HH:00
      0 H D * *       → monthly on day D at HH:00
      0 H * * DOW     → weekly on day-of-week at HH:00
      M H * * *       → daily at HH:MM
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression (need 5 fields): {cron_expr!r}")

    minute, hour, dom, month, dow = parts

    # Every N minutes
    if re.match(r'^\*/(\d+)$', minute) and hour == '*':
        n = re.match(r'^\*/(\d+)$', minute).group(1)
        return ['/sc', 'MINUTE', '/mo', n]

    # Wildcard every minute
    if minute == '*' and hour == '*':
        return ['/sc', 'MINUTE', '/mo', '1']

    # Hourly  (0 * * * *)
    if minute == '0' and hour == '*':
        return ['/sc', 'HOURLY', '/mo', '1']

    # Day-of-week weekly  (M H * * DOW)
    if dom == '*' and month == '*' and dow != '*':
        day_map = {'0':'SUN','1':'MON','2':'TUE','3':'WED',
                   '4':'THU','5':'FRI','6':'SAT','7':'SUN'}
        day_str = day_map.get(dow, dow)
        st = f"{int(hour):02d}:{int(minute):02d}"
        return ['/sc', 'WEEKLY', '/d', day_str, '/st', st]

    # Monthly  (M H D * *)
    if dom != '*' and month == '*' and dow == '*':
        st = f"{int(hour):02d}:{int(minute):02d}"
        return ['/sc', 'MONTHLY', '/d', dom, '/st', st]

    # Daily at specific time  (M H * * *)
    if dom == '*' and month == '*' and dow == '*':
        st = f"{int(hour):02d}:{int(minute):02d}"
        return ['/sc', 'DAILY', '/st', st]

    # Fallback: run daily
    st = '00:00'
    if hour.isdigit() and minute.isdigit():
        st = f"{int(hour):02d}:{int(minute):02d}"
    return ['/sc', 'DAILY', '/st', st]


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def add_cron(cron_expr, command):
    """
    Create a Windows scheduled task equivalent to:
        {cron_expr}  {command}

    Returns the task name on success, raises on failure.
    """
    task_name = _task_name(command)

    # Ensure folder exists (best-effort; older schtasks may not support folders)
    _run(['schtasks', '/create', '/tn', _TASK_FOLDER,
          '/tr', 'cmd /c echo voidpanel', '/sc', 'ONCE', '/st', '00:00',
          '/f', '/rl', 'HIGHEST'], timeout=10)

    try:
        sc_args = _cron_to_schtasks(cron_expr)
    except ValueError:
        sc_args = ['/sc', 'DAILY', '/st', '00:00']

    # Wrap bare python/scripts in cmd /c so env vars are available
    tr_command = command if command.startswith('"') else f'cmd /c "{command}"'

    cmd = (
        ['schtasks', '/create', '/tn', task_name,
         '/tr', tr_command,
         '/f', '/rl', 'HIGHEST', '/ru', 'SYSTEM']
        + sc_args
    )
    ok, out, err = _run(cmd, timeout=30)

    if ok or 'success' in (out + err).lower():
        reg = _load_reg()
        reg[task_name] = {'cron': cron_expr, 'command': command}
        _save_reg(reg)
        return task_name
    raise RuntimeError(f"schtasks create failed: {err or out}")


def delete_cron(command_substring):
    """
    Delete all scheduled tasks whose command contains command_substring.
    Mirrors: filter crontab then reload.
    """
    reg = _load_reg()
    deleted = []
    for tn, info in list(reg.items()):
        if command_substring in info.get('command', ''):
            ok, _, _ = _run(['schtasks', '/delete', '/tn', tn, '/f'])
            if ok:
                del reg[tn]
                deleted.append(tn)
    _save_reg(reg)
    return deleted


def list_crons():
    """
    Return list of (cron_expr, command) for all VoidPanel tasks.
    """
    reg = _load_reg()
    return [(v['cron'], v['command']) for v in reg.values()]


def crontab_minus(cron_lines):
    """
    Bulk-load cron jobs from a string (same format as crontab -).
    Each non-empty, non-comment line: "M H DoM Mon DoW command..."
    Clears existing VoidPanel tasks from registry first.
    """
    # Clear existing
    reg = _load_reg()
    for tn in list(reg.keys()):
        _run(['schtasks', '/delete', '/tn', tn, '/f'])
    _save_reg({})

    added = []
    for line in cron_lines.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        cron_expr = ' '.join(parts[:5])
        command   = parts[5]
        try:
            add_cron(cron_expr, command)
            added.append(line)
        except Exception:
            pass
    return added


def get_crontab_text():
    """
    Return current cron jobs as a crontab-style text block.
    """
    jobs = list_crons()
    if not jobs:
        return ''
    return '\n'.join(f'{expr}  {cmd}' for expr, cmd in jobs) + '\n'
