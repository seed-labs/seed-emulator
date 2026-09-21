<?php
ini_set('display_errors', '0');
header('Cache-Control: no-store');
if (($_SERVER['HTTPS'] ?? '') !== 'on') { http_response_code(403); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit; }
$source = $_POST['source_id'] ?? null;
$token = $_POST['token'] ?? null;
if (!is_string($source) || !is_string($token)) { http_response_code(401); exit; }
$source = trim($source);
$token = trim($token);
try {
    $config = json_decode(file_get_contents('/opt/seedemu/loom/source-auth.json'), true, 512, JSON_THROW_ON_ERROR);
    $entry = $config[$source] ?? null;
    if (!$entry || !hash_equals($entry['token_sha256'], hash('sha256', $token)) ||
        !hash_equals($entry['address'], $_SERVER['REMOTE_ADDR'] ?? '')) {
        http_response_code(401); exit;
    }
    unset($token, $_POST['token']);
    require '/opt/loom/bootstrap/app.php';
    $find = $pdo->prepare('SELECT id, email, username, status, verified, roles_mask, force_logout,
        tfa_enabled, auth_method FROM users WHERE email = ?');
    $find->execute([$entry['email']]);
    $user = $find->fetch(PDO::FETCH_ASSOC);
    if (!$user || (int)$user['verified'] !== 1 || (int)$user['status'] !== 0 ||
        (int)$user['tfa_enabled'] !== 0 || $user['auth_method'] !== 'password') {
        http_response_code(403); exit;
    }
    class SeedEmuSourceAuth extends \Pinga\Auth\UserManager {
        public function __construct(PDO $pdo) { parent::__construct($pdo); }
        public function establish(array $user): void {
            $this->onLoginSuccessful($user['id'], $user['email'], $user['username'],
                $user['status'], $user['roles_mask'], $user['force_logout'], false);
        }
    }
    $auth = new \Pinga\Auth\Auth($pdo);
    if (!$auth->isLoggedIn() || $auth->getUserId() !== (int)$user['id']) {
        (new SeedEmuSourceAuth($pdo))->establish($user);
    }
    session_write_close();
    http_response_code(204);
} catch (Throwable $error) {
    error_log("SeedEmu source auth failed: " . get_class($error) . ": " . $error->getMessage());
    http_response_code(500);
}

