<?php
/**
 * VoidPanel SSO Auto-Login Plugin for Roundcube 1.6.x
 *
 * Correct approach for Roundcube 1.6:
 * - Uses 'authenticate' hook (not 'startup') so it fires during the
 *   normal Roundcube login flow without fighting session management
 * - Django view POSTs a form to /?_task=login&_action=login with
 *   vp_token as a hidden field — Roundcube processes it as a normal login
 * - This hook reads the token, loads the credentials, and injects them
 *   as the user/pass for Roundcube's own IMAP login call
 *
 * Installation:
 * 1. Place this file at: /var/www/roundcube/plugins/vp_autologin/vp_autologin.php
 * 2. Add 'vp_autologin' to $config['plugins'] in config/config.inc.php
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

        // Sanitize — only allow UUID characters
        $token    = preg_replace('/[^a-f0-9\-]/', '', $token);
        $sso_file = "/var/www/roundcube/temp/rc_sso_{$token}";

        if (!file_exists($sso_file)) {
            return $args;  // Token expired or already used
        }

        // Read then immediately delete — strictly one-time use
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

        // Inject credentials into Roundcube's authenticate args
        // Roundcube will use these for its own IMAP login call
        $args['user']  = $email;
        $args['pass']  = $password;
        $args['host']  = 'localhost';
        $args['valid'] = true;

        return $args;
    }
}
