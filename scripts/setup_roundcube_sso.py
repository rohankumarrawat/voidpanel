#!/usr/bin/env python3
"""
VoidPanel – Roundcube SSO Setup
================================
Idempotent: safe to run multiple times.
Installs the vp_autologin Roundcube plugin and configures the temp directory.

Run as root:
    python3 scripts/setup_roundcube_sso.py

Or called automatically by the Django manage command:
    python3 manage.py setup_roundcube_sso
"""
import os
import sys
import shutil
import subprocess
import textwrap
import stat

# ── Paths ─────────────────────────────────────────────────────────────────────
ROUNDCUBE_DIR  = "/var/www/roundcube"
PLUGIN_DIR     = os.path.join(ROUNDCUBE_DIR, "plugins", "vp_autologin")
PLUGIN_FILE    = os.path.join(PLUGIN_DIR, "vp_autologin.php")
TEMP_DIR       = os.path.join(ROUNDCUBE_DIR, "temp")
RC_CONFIG_FILE = os.path.join(ROUNDCUBE_DIR, "config", "config.inc.php")

# Path to the plugin source relative to this script
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_PLUGIN = os.path.join(SCRIPT_DIR, "..", "roundcube_plugins", "vp_autologin", "vp_autologin.php")

# Inline plugin PHP (fallback if repo file not found)
PLUGIN_PHP = textwrap.dedent(r"""
    <?php
    /**
     * VoidPanel SSO Auto-Login Plugin for Roundcube 1.6.x
     *
     * Uses the 'authenticate' hook so Roundcube manages its own session.
     * Django panel writes a one-time token file; this plugin reads it and
     * injects credentials into Roundcube's normal login flow.
     *
     * Token file format: /var/www/roundcube/temp/rc_sso_<uuid>
     *   Line 1: email address
     *   Line 2: password (plain text — file is deleted immediately after read)
     */
    class vp_autologin extends rcube_plugin
    {
        public $task = 'login';

        public function init()
        {
            $this->add_hook('authenticate', [$this, 'handle_vp_token']);
        }

        public function handle_vp_token($args)
        {
            // Accept token from POST (auto-submit form) or GET (fallback redirect)
            $token = rcube_utils::get_input_value(
                'vp_token',
                rcube_utils::INPUT_POST | rcube_utils::INPUT_GET
            );

            if (empty($token) || !preg_match('/^[a-f0-9\-]{36}$/', $token)) {
                return $args;
            }

            $token    = preg_replace('/[^a-f0-9\-]/', '', $token);
            $sso_file = "/var/www/roundcube/temp/rc_sso_{$token}";

            if (!file_exists($sso_file)) {
                return $args;  // Token expired or already used
            }

            // One-time use: read then immediately delete
            $content = file_get_contents($sso_file);
            @unlink($sso_file);

            $lines = explode("\n", trim($content), 2);
            if (count($lines) < 2) {
                return $args;
            }

            $email    = trim($lines[0]);
            $password = trim($lines[1]);

            if (empty($email) || empty($password)) {
                return $args;
            }

            // Inject credentials into Roundcube's authenticate flow
            $args['user']  = $email;
            $args['pass']  = $password;
            $args['host']  = 'localhost';
            $args['valid'] = true;

            return $args;
        }
    }
""").strip()


def run(cmd, **kwargs):
    """Run a command, return True on success."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"  WARN: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
        print(f"        {result.stderr.strip()[:200]}")
    return result.returncode == 0


def check_roundcube():
    """Return True if Roundcube is installed."""
    return os.path.isdir(ROUNDCUBE_DIR) and os.path.isfile(
        os.path.join(ROUNDCUBE_DIR, "index.php")
    )


def install_plugin():
    """Create plugin directory and write the PHP file."""
    os.makedirs(PLUGIN_DIR, exist_ok=True)

    # Prefer the repo copy; fall back to inline
    if os.path.isfile(REPO_PLUGIN):
        shutil.copy2(REPO_PLUGIN, PLUGIN_FILE)
        print(f"  ✔  Plugin installed from repo: {PLUGIN_FILE}")
    else:
        with open(PLUGIN_FILE, "w") as f:
            f.write(PLUGIN_PHP + "\n")
        print(f"  ✔  Plugin installed (inline): {PLUGIN_FILE}")

    # Ownership
    run(["chown", "www-data:www-data", PLUGIN_DIR])
    run(["chown", "www-data:www-data", PLUGIN_FILE])
    os.chmod(PLUGIN_FILE, 0o644)


def setup_temp_dir():
    """Create the temp dir with correct ownership and sticky-bit permissions."""
    os.makedirs(TEMP_DIR, exist_ok=True)
    run(["chown", "www-data:www-data", TEMP_DIR])

    # chmod 1777: sticky bit + world-writable so Django (www-data) can write
    # tokens and php-fpm (also www-data) can read them
    os.chmod(TEMP_DIR, stat.S_ISVTX | 0o777)
    print(f"  ✔  Temp dir ready: {TEMP_DIR}  (chmod 1777, owner www-data)")


def register_plugin_in_config():
    """Add 'vp_autologin' to $config['plugins'] if not already present."""
    if not os.path.isfile(RC_CONFIG_FILE):
        print(f"  !  Roundcube config not found: {RC_CONFIG_FILE} — skipping registration")
        return

    with open(RC_CONFIG_FILE, "r") as f:
        content = f.read()

    if "vp_autologin" in content:
        print("  ✔  Plugin already registered in Roundcube config")
        return

    # Insert after the plugins array opening, or append before ?>
    if "$config['plugins']" in content:
        # Add to existing plugins array
        updated = content.replace(
            "$config['plugins'] = [",
            "$config['plugins'] = ['vp_autologin', "
        )
        # Handle already-formatted arrays
        if updated == content:
            updated = content.replace(
                "$config['plugins'] = ['",
                "$config['plugins'] = ['vp_autologin', '"
            )
    else:
        # No plugins line — prepend to config
        insert = "\n$config['plugins'] = ['vp_autologin'];\n"
        if "?>" in content:
            updated = content.replace("?>", insert + "?>", 1)
        else:
            updated = content + insert

    with open(RC_CONFIG_FILE, "w") as f:
        f.write(updated)

    print("  ✔  Plugin registered in Roundcube config")


def verify():
    """Quick sanity check."""
    ok = True
    for path, desc in [
        (PLUGIN_FILE, "Plugin PHP file"),
        (TEMP_DIR,    "Temp directory"),
    ]:
        if os.path.exists(path):
            print(f"  ✔  {desc}: {path}")
        else:
            print(f"  ✘  {desc} MISSING: {path}")
            ok = False

    with open(RC_CONFIG_FILE, "r") as f:
        if "vp_autologin" in f.read():
            print("  ✔  Plugin registered in config")
        else:
            print("  ✘  Plugin NOT in Roundcube config")
            ok = False

    return ok


def main():
    if os.geteuid() != 0:
        print("[!] This script must be run as root (sudo python3 setup_roundcube_sso.py)")
        sys.exit(1)

    print("\n== VoidPanel Roundcube SSO Setup ==\n")

    if not check_roundcube():
        print(f"  [!] Roundcube not found at {ROUNDCUBE_DIR}.")
        print("      Install Roundcube first, then re-run this script.")
        sys.exit(1)

    print("[1] Installing vp_autologin plugin...")
    install_plugin()

    print("[2] Setting up temp directory...")
    setup_temp_dir()

    print("[3] Registering plugin in Roundcube config...")
    register_plugin_in_config()

    print("[4] Verifying installation...")
    if verify():
        print("\n✅  Roundcube SSO is ready.\n")
    else:
        print("\n⚠️   Setup completed with warnings. Check output above.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
