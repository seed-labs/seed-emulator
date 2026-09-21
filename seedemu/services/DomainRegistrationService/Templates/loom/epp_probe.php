<?php
declare(strict_types=1);

require '/opt/loom/vendor/autoload.php';
Dotenv\Dotenv::createImmutable('/opt/loom')->load();
require '/opt/loom/bootstrap/helper.php';

$configPath = $argv[1] ?? '/opt/seedemu/loom/epp-probe.json';
$config = json_decode(
    file_get_contents($configPath),
    true,
    16,
    JSON_THROW_ON_ERROR
);
$pdo = new PDO(
    'mysql:host=' . $_ENV['DB_HOST'] . ';port=' . $_ENV['DB_PORT']
        . ';dbname=' . $_ENV['DB_DATABASE'] . ';charset=utf8mb4',
    $_ENV['DB_USERNAME'],
    $_ENV['DB_PASSWORD'],
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
);
$find = $pdo->prepare("SELECT api_endpoint, credentials FROM providers
    WHERE tld = ? AND status = 'active'");
$find->execute([$config['tld']]);
$provider = $find->fetch(PDO::FETCH_ASSOC);
if (!$provider) {
    throw new RuntimeException('Active Loom EPP provider not found');
}
$credentials = json_decode($provider['credentials'], true, 64, JSON_THROW_ON_ERROR);
[$host, $port] = explode(':', $provider['api_endpoint'], 2);
$epp = connectEpp(
    'generic', $host, (int)$port,
    $credentials['cafile'], $credentials['cert_file'], $credentials['key_file'],
    $credentials['passphrase'], $credentials['auth']['username'],
    $credentials['auth']['password']
);
$reply = $epp->domainCheck(['domains' => [$config['domain']]]);
$epp->logout();
if (isset($reply['error'])) {
    throw new RuntimeException((string)$reply['error']);
}
echo json_encode([
    'status' => 'ok',
    'transport' => 'epp-over-tls',
    'client' => 'loom',
    'peer' => $provider['api_endpoint'],
    'operation' => 'domain-check',
    'resource' => $config['domain'],
], JSON_UNESCAPED_SLASHES | JSON_THROW_ON_ERROR) . PHP_EOL;
