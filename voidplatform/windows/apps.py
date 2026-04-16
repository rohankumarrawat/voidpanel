"""
Windows Python/MERN app deployment using:
  - Python apps  → waitress-serve WSGI server + Windows Service via sc.exe/NSSM
  - MERN apps    → pm2 (Node.js process manager for Windows)

These are drop-in replacements for the Linux systemd + uwsgi approach.
"""
import os
import sys
import subprocess
import textwrap
from ..config import WindowsPaths as paths

_BASE_PORT_PYTHON = 9200   # Start allocating from here for Python apps
_BASE_PORT_MERN   = 3001   # MERN apps start from here


def _run(cmd, shell=False, timeout=30):
    """Run command silently, return (success, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, shell=shell, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        return r.returncode == 0, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return False, '', str(e)


# ─────────────────────────────── SERVICE REGISTRY ──────────────────────────────

def _registry_file():
    """Persistent JSON file that maps app name → port so ports survive restarts."""
    return os.path.join(paths.PANEL_ROOT, 'windows_apps.json')


def _load_registry():
    import json
    f = _registry_file()
    if os.path.exists(f):
        try:
            with open(f) as fp:
                return json.load(fp)
        except Exception:
            pass
    return {}


def _save_registry(reg):
    import json
    os.makedirs(os.path.dirname(_registry_file()), exist_ok=True)
    with open(_registry_file(), 'w') as fp:
        json.dump(reg, fp, indent=2)


def _allocate_port(kind='python'):
    """Pick the next free port for a new app."""
    reg = _load_registry()
    used = {v.get('port') for v in reg.values() if v.get('port')}
    base = _BASE_PORT_PYTHON if kind == 'python' else _BASE_PORT_MERN
    port = base
    while port in used:
        port += 1
    return port


# ─────────────────────────────── NSSM HELPER ───────────────────────────────────

def _nssm_path():
    """Find nssm.exe — bundled with VoidPanel or in PATH."""
    bundled = os.path.join(paths.PANEL_ROOT, 'tools', 'nssm.exe')
    if os.path.exists(bundled):
        return bundled
    # Try PATH
    ok, out, _ = _run(['where', 'nssm'])
    if ok and out:
        return out.splitlines()[0].strip()
    return None


def _sc_create_service(name, executable, args, working_dir, display_name=None):
    """
    Create + start a Windows service.
    Prefers NSSM (cleaner), falls back to sc.exe + wrapper batch.
    Returns (success, message).
    """
    nssm = _nssm_path()

    if nssm:
        # Use NSSM for clean service management
        _run([nssm, 'remove', name, 'confirm'])  # Remove if exists
        ok, out, err = _run([nssm, 'install', name, executable] + args)
        if ok or 'installed' in (out + err).lower():
            _run([nssm, 'set', name, 'AppDirectory', working_dir])
            _run([nssm, 'set', name, 'DisplayName', display_name or name])
            _run([nssm, 'set', name, 'Start', 'SERVICE_AUTO_START'])
            ok2, _, err2 = _run([nssm, 'start', name])
            return True, f'Service {name!r} created and started via NSSM.'
        return False, f'NSSM install failed: {err}'

    else:
        # Fallback: write a .bat launcher + sc.exe
        bat_path = os.path.join(paths.PANEL_ROOT, 'services', f'{name}.bat')
        os.makedirs(os.path.dirname(bat_path), exist_ok=True)
        args_str = ' '.join(f'"{a}"' if ' ' in a else a for a in args)
        bat_content = f'@echo off\ncd /d "{working_dir}"\n"{executable}" {args_str}\n'
        with open(bat_path, 'w') as f:
            f.write(bat_content)

        # Create service pointing to cmd.exe running the batch file
        cmd_exe = r'C:\Windows\System32\cmd.exe'
        binpath = f'"{cmd_exe}" /C "{bat_path}"'
        _run(['sc', 'delete', name])
        ok, out, err = _run(['sc', 'create', name, 'binPath=', binpath,
                              'start=', 'auto', 'DisplayName=', display_name or name])
        _run(['sc', 'start', name])
        if ok:
            return True, f'Service {name!r} created via sc.exe.'
        return False, f'sc.exe failed: {err}'


def _sc_stop_delete_service(name):
    """Stop and remove a Windows service."""
    nssm = _nssm_path()
    if nssm:
        _run([nssm, 'stop', name])
        _run([nssm, 'remove', name, 'confirm'])
    else:
        _run(['sc', 'stop', name])
        _run(['sc', 'delete', name])


# ─────────────────────── PYTHON APP DEPLOYMENT ─────────────────────────────────

def deploy_python_app(fre_dir, name, domain):
    """
    Deploy a Python/Django app on Windows using waitress-serve as WSGI server.

    Architecture (Windows):
      - App lives in: HOME_BASE/{fre_dir}/{name}/
      - waitress-serve listens on 127.0.0.1:{port}
      - nginx proxy_passes to http://127.0.0.1:{port}/
      - Registered as a Windows service named 'voidpy_{name}'

    Returns (port, success, message).
    """
    app_dir = os.path.join(paths.HOME_BASE, fre_dir, name)
    os.makedirs(os.path.join(app_dir, 'static'), exist_ok=True)

    port = _allocate_port('python')
    svc_name = f'voidpy_{name}'

    # Find Python executable (prefer venv if it exists)
    venv_python = os.path.join(app_dir, 'venv', 'Scripts', 'python.exe')
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable

    # Install waitress into the venv / global env
    _run([python_exe, '-m', 'pip', 'install', 'waitress', '-q'])

    # Create the service: python -m waitress --port=PORT name.wsgi:application
    success, msg = _sc_create_service(
        name=svc_name,
        executable=python_exe,
        args=['-m', 'waitress', f'--port={port}', f'{name}.wsgi:application'],
        working_dir=app_dir,
        display_name=f'VoidPanel Python App — {name}',
    )

    # Update registry
    reg = _load_registry()
    reg[name] = {'type': 'python', 'port': port, 'dir': fre_dir, 'svc': svc_name}
    _save_registry(reg)

    return port, success, msg


def delete_python_app(name):
    """Stop/remove Python app Windows service and update registry."""
    reg = _load_registry()
    info = reg.pop(name, {})
    svc_name = info.get('svc', f'voidpy_{name}')
    _sc_stop_delete_service(svc_name)
    _save_registry(reg)


def get_python_app_port(name):
    """Return the TCP port for an existing Python app (or None)."""
    return _load_registry().get(name, {}).get('port')


def python_nginx_location_block(name, port):
    """Generate an nginx location block for a Windows Python app (HTTP proxy)."""
    return f"""
    location / {{
        proxy_pass http://127.0.0.1:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location /static/ {{
        alias {os.path.join(paths.HOME_BASE, name, 'static').replace(os.sep, '/')}/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }}
    """


# ─────────────────────── MERN APP DEPLOYMENT ───────────────────────────────────

def deploy_mern_app(fre_dir, name, domain, port=None):
    """
    Deploy a MERN/Node.js app on Windows using PM2 (works natively on Windows).

    Architecture (Windows):
      - App lives in: HOME_BASE/{fre_dir}/{name}/
      - PM2 manages the node process on port {port}
      - nginx proxy_passes to http://127.0.0.1:{port}/api/
      - React build served from frontend/build/

    Returns (port, success, message).
    """
    app_dir = os.path.join(paths.HOME_BASE, fre_dir, name)
    os.makedirs(app_dir, exist_ok=True)

    if port is None:
        port = _allocate_port('mern')

    # Check if pm2 is available
    ok_pm2, pm2_path, _ = _run(['where', 'pm2'])
    if not ok_pm2:
        # Try to install pm2 globally via npm
        _run(['npm', 'install', '-g', 'pm2'], timeout=120)
        ok_pm2, pm2_path, _ = _run(['where', 'pm2'])

    if ok_pm2:
        pm2 = pm2_path.splitlines()[0].strip() if pm2_path else 'pm2'
        # Delete existing pm2 process if any
        _run([pm2, 'delete', name])
        # Start the backend
        backend_script = os.path.join(app_dir, 'server.js')
        if not os.path.exists(backend_script):
            backend_script = os.path.join(app_dir, 'index.js')
        env = {**os.environ, 'PORT': str(port)}
        ok, out, err = _run([pm2, 'start', backend_script, '--name', name,
                              '--env', 'production'], timeout=60)
        # Save pm2 process list so it survives reboot
        _run([pm2, 'save'])
        # Set pm2 to start on boot (Windows)
        _run([pm2, 'startup', 'windows'])
        success = ok
        msg = out or err
    else:
        # Fallback: Windows service via sc.exe running node directly
        node_ok, node_path, _ = _run(['where', 'node'])
        if not node_ok:
            return port, False, 'Node.js not found. Install Node.js first.'
        node_exe = node_path.splitlines()[0].strip()
        backend = os.path.join(app_dir, 'server.js')
        success, msg = _sc_create_service(
            name=f'voidmern_{name}',
            executable=node_exe,
            args=[backend],
            working_dir=app_dir,
            display_name=f'VoidPanel MERN App — {name}',
        )

    # Update registry
    reg = _load_registry()
    reg[name] = {'type': 'mern', 'port': port, 'dir': fre_dir}
    _save_registry(reg)

    return port, success, msg


def delete_mern_app(name):
    """Stop/remove MERN app from pm2/service and update registry."""
    reg = _load_registry()
    info = reg.pop(name, {})
    _save_registry(reg)

    ok_pm2, pm2_path, _ = _run(['where', 'pm2'])
    if ok_pm2:
        pm2 = pm2_path.splitlines()[0].strip()
        _run([pm2, 'delete', name])
        _run([pm2, 'save'])
    else:
        _sc_stop_delete_service(f'voidmern_{name}')


def get_mern_app_port(name):
    """Return the TCP port for an existing MERN app (or None)."""
    return _load_registry().get(name, {}).get('port')


def mern_nginx_location_block(name, port, static_path=''):
    """Generate an nginx location block for a Windows MERN app."""
    static_alias = static_path.replace(os.sep, '/') + '/' if static_path else ''
    block = f"""
    location / {{
        try_files $uri /index.html;
    }}
    location /api/ {{
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }}
    """
    if static_alias:
        block += f"""
    location /static/ {{
        alias {static_alias};
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }}
    """
    return block


# ─────────────────────── UPDATE PANEL ─────────────────────────────────────────

def update_panel_windows():
    """
    Self-update VoidPanel on Windows using PowerShell.
    Downloads the latest release zip and replaces panel files.
    Returns (success, message).
    """
    ps_script = textwrap.dedent(r"""
        $ErrorActionPreference = 'Stop'
        $updateUrl = 'https://voidpanel.com/updatepanel.zip'
        $tmpZip = "$env:TEMP\voidpanel_update.zip"
        $tmpDir = "$env:TEMP\voidpanel_update"

        Write-Host "[1/4] Downloading update..."
        Invoke-WebRequest -Uri $updateUrl -OutFile $tmpZip -UseBasicParsing

        Write-Host "[2/4] Extracting..."
        if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
        Expand-Archive -Path $tmpZip -DestinationPath $tmpDir

        Write-Host "[3/4] Applying update..."
        $panelRoot = $env:VOIDPANEL_BASE
        if (-not $panelRoot) { $panelRoot = 'C:\VoidPanel' }
        Copy-Item "$tmpDir\*" -Destination $panelRoot -Recurse -Force

        Write-Host "[4/4] Cleaning up..."
        Remove-Item $tmpZip -Force
        Remove-Item $tmpDir -Recurse -Force
        Write-Host "VoidPanel updated successfully!"
    """)

    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
             '-Command', ps_script],
            capture_output=True, text=True, timeout=300,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        if result.returncode == 0:
            return True, 'VoidPanel updated successfully via PowerShell.'
        return False, f'Update failed: {result.stderr.strip()}'
    except Exception as e:
        return False, f'Update error: {e}'
