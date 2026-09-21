<?php
require '/opt/loom/vendor/autoload.php';
Dotenv\Dotenv::createImmutable('/opt/loom')->load();
$dsn = 'mysql:host=' . $_ENV['DB_HOST'] . ';port=' . $_ENV['DB_PORT']
    . ';dbname=' . $_ENV['DB_DATABASE'] . ';charset=utf8mb4';
$pdo = new PDO($dsn, $_ENV['DB_USERNAME'], $_ENV['DB_PASSWORD'], [
    PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
]);
$sql = file_get_contents('/opt/seedemu/loom/provider.sql');
if ($sql === false || trim($sql) === '') {
    throw new RuntimeException('Loom provider SQL is empty');
}
$pdo->exec($sql);

