"""Opt-in SeedEmu source authentication adapter for the pinned Loom application."""

SOURCE_AUTH_BOOTSTRAP = r'''<?php
require '/opt/loom/vendor/autoload.php';
Dotenv\Dotenv::createImmutable('/opt/loom')->load();
$pdo = new PDO('mysql:host=' . $_ENV['DB_HOST'] . ';dbname=' . $_ENV['DB_DATABASE'] . ';charset=utf8',
    $_ENV['DB_USERNAME'], $_ENV['DB_PASSWORD'], [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$auth = new \Pinga\Auth\Auth($pdo);
$config = json_decode(file_get_contents('/opt/seedemu/loom/source-auth.json'), true, 512, JSON_THROW_ON_ERROR);
foreach ($config as $source => $entry) {
    $find = $pdo->prepare('SELECT id, username FROM users WHERE email = ?');
    $find->execute([$entry['email']]);
    $user = $find->fetch(PDO::FETCH_ASSOC);
    if ($user && $user['username'] !== $entry['username']) {
        throw new RuntimeException('Source account conflicts with an existing account');
    }
    if (!$user) {
        // Native administration API creates an already verified account.
        $id = $auth->admin()->createUserWithUniqueUsername(
            $entry['email'], bin2hex(random_bytes(16)), $entry['username']);
        $auth->admin()->addRoleForUserById($id, \Pinga\Auth\Role::COLLABORATOR);
        $pdo->prepare('UPDATE users SET currency = ?, credit_limit = ? WHERE id = ?')
            ->execute(['USD', $entry['credit_limit'] ?? 0, $id]);
        $insert = $pdo->prepare('INSERT INTO users_contact
            (user_id, type, first_name, last_name, street1, city, pc, cc, voice, email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)');
        foreach (['owner', 'admin', 'billing', 'tech', 'abuse'] as $type) {
            $insert->execute([$id, $type, 'SeedEmu', 'Example', '150 Simulation Road',
                'Simulation', '10000', 'US', '+1.5550100', $entry['email']]);
        }
    }
    $userId = (int)($user['id'] ?? $id);
    $pdo->prepare('UPDATE users SET credit_limit = ? WHERE id = ?')
        ->execute([$entry['credit_limit'] ?? 0, $userId]);
}
echo "SeedEmu source accounts ready\n";
'''

SOURCE_AUTH_ENDPOINT = r'''<?php
// Separate opt-in bearer-token endpoint. Native Loom forms retain CSRF checks.
ini_set('display_errors', '0');
header('Cache-Control: no-store');
if (($_SERVER['HTTPS'] ?? '') !== 'on') { http_response_code(403); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(405); exit; }
$source = $_POST['source_id'] ?? null;
$token = $_POST['token'] ?? null;
if (!is_string($source) || !is_string($token)) { http_response_code(401); exit; }
// SeedEmu emits text files with a final newline.
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
    // Use the native session creator (including session-ID rotation), not a
    // hand-written set of PHP session fields or an administrator impersonation.
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
    // No token, request body or database detail is returned to the caller.
    error_log("SeedEmu source auth failed: " . get_class($error) . ": " . $error->getMessage());
    http_response_code(500);
}
'''
