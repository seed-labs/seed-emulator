<?php
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

