<?php
class vp_autologin extends rcube_plugin
{
    public $task = 'login';
    private $user = null;
    private $pass = null;

    function init()
    {
        if (!empty($_GET['vp_token'])) {
            $token = preg_replace('/[^a-zA-Z0-9-]/', '', $_GET['vp_token']);
            $file = "/tmp/rc_sso_" . $token;
            if (file_exists($file)) {
                $lines = file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
                if (count($lines) >= 2) {
                    $this->user = $lines[0];
                    $this->pass = $lines[1];
                }
                @unlink($file);
            }
        }

        $this->add_hook('startup', array($this, 'startup'));
        $this->add_hook('authenticate', array($this, 'authenticate'));
    }

    function startup($args)
    {
        if (empty($_SESSION['user_id']) && $this->user && $this->pass) {
            $args['action'] = 'login';
        }
        return $args;
    }

    function authenticate($args)
    {
        if ($this->user && $this->pass) {
            $args['user'] = $this->user;
            $args['pass'] = $this->pass;
            $args['cookiecheck'] = false;
            $args['valid'] = true;
            $args['abort'] = false;
        }
        return $args;
    }
}
?>