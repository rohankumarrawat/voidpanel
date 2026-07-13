<?php
/**
 * VoidPanel phpMyAdmin SSO Gateway
 * Deploy to: /usr/share/phpmyadmin/vp_sso.php
 * 
 * Accepts POST with temp_user + temp_password, creates a session, redirects to PMA.
 */
session_start();

// Only allow POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    die('Method not allowed.');
}

$user     = isset($_POST['temp_user'])     ? trim($_POST['temp_user'])     : '';
$password = isset($_POST['temp_password']) ? trim($_POST['temp_password']) : '';

if (empty($user) || empty($password)) {
    http_response_code(400);
    die('Missing credentials.');
}

// Basic validation — only allow vp_temp_ prefixed users
if (!preg_match('/^vp_temp_[a-z0-9]+$/', $user)) {
    http_response_code(403);
    die('Forbidden.');
}

// Set phpMyAdmin session variables for auto-login
$_SESSION['PMA_single_signon_user']     = $user;
$_SESSION['PMA_single_signon_password'] = $password;
$_SESSION['PMA_single_signon_host']     = 'localhost';
$_SESSION['PMA_single_signon_port']     = '3306';

// Write a cookie so PMA's signon handler picks up the session
$session_id = session_id();

// Redirect to PMA index — it will pick up the session
header('Location: index.php');
exit;
