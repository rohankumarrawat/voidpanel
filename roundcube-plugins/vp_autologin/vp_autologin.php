<?php
/**
 * VoidPanel Auto-Login Plugin for Roundcube
 * Intercepts ?vp_token=<uuid> on the login page and auto-authenticates.
 * 
 * Token file format: /var/www/roundcube/temp/rc_sso_<uuid>
 * File contains: email\npassword
 */
class vp_autologin extends rcube_plugin
{
    public $task = 'login';

    public function init()
    {
        $this->add_hook('startup', [$this, 'handle_vp_token']);
    }

    public function handle_vp_token($args)
    {
        $token = rcube_utils::get_input_value('vp_token', rcube_utils::INPUT_GET);
        if (empty($token) || !preg_match('/^[a-f0-9\-]{36}$/', $token)) {
            return $args;
        }

        // Sanitize token to prevent path traversal
        $token    = preg_replace('/[^a-f0-9\-]/', '', $token);
        $sso_file = "/var/www/roundcube/temp/rc_sso_{$token}";

        if (!file_exists($sso_file)) {
            return $args;
        }

        $content = file_get_contents($sso_file);
        
        $lines    = explode("\n", trim($content), 2);
        if (count($lines) < 2) return $args;

        $email    = trim($lines[0]);
        $password = trim($lines[1]);

        if (empty($email) || empty($password)) return $args;

        // Perform Roundcube's internal login
        $rcmail = rcmail::get_instance();
        $auth   = $rcmail->login($email, $password, '127.0.0.1', false);

        if ($auth) {
            // Delete token securely
            @unlink($sso_file);
            
            // Set session environment natively
            $rcmail->session->remove('temp');
            $rcmail->session->regenerate_id(false);
            
            // CRITICAL: Send Auth Cookie before redirect to pass anti-hijacking checks
            $rcmail->session->set_auth_cookie();
            $rcmail->log_login();
            
            // Redirect smoothly to inbox
            $rcmail->output->redirect(['_task' => 'mail']);
        }

        // If login fails, fall through to normal login page
        return $args;
    }
}
