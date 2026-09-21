<?php
declare(strict_types=1);

$settings = json_decode(<<<'JSON'
__SEED_SETTINGS_JSON__
JSON, true, 512, JSON_THROW_ON_ERROR);

$pdo = new PDO(
    'mysql:unix_socket=/run/mysqld/mysqld.sock;dbname=' . $settings['database'] . ';charset=utf8mb4',
    'root',
    '',
    [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
);

$pdo->beginTransaction();
try {
    // Disable the public demonstration EPP credentials shipped in the sample schema.
    $disabled = password_hash(bin2hex(random_bytes(32)), PASSWORD_ARGON2ID);
    $configuredClids = array_column($settings['registrars'], 'clid');
    if ($configuredClids === []) {
        $pdo->prepare('UPDATE registrar SET pw = :pw')->execute(['pw' => $disabled]);
    } else {
        $placeholders = implode(',', array_fill(0, count($configuredClids), '?'));
        $stmt = $pdo->prepare("UPDATE registrar SET pw = ? WHERE clid NOT IN ($placeholders)");
        $stmt->execute(array_merge([$disabled], $configuredClids));
    }

    // The upstream schema also ships .test and .com.test demonstration TLDs.
    // Remove only those untouched sample rows when this emulation did not ask
    // for them, so the upstream Zone Writer does not emit unrelated zones.
    $configuredTlds = array_map(
        static fn(string $tld): string => '.' . ltrim(strtolower($tld), '.'),
        $settings['tlds']
    );
    foreach (['.test', '.com.test'] as $sampleTld) {
        if (in_array($sampleTld, $configuredTlds, true)) {
            continue;
        }
        $stmt = $pdo->prepare(
            'SELECT id FROM domain_tld WHERE tld = :tld '
            . 'AND NOT EXISTS (SELECT 1 FROM domain WHERE domain.tldid = domain_tld.id) '
            . 'AND NOT EXISTS (SELECT 1 FROM application WHERE application.tldid = domain_tld.id)'
        );
        $stmt->execute(['tld' => $sampleTld]);
        $sampleTldId = $stmt->fetchColumn();
        if ($sampleTldId !== false) {
            $pdo->prepare('DELETE FROM domain_restore_price WHERE tldid = :id')
                ->execute(['id' => $sampleTldId]);
            $pdo->prepare('DELETE FROM domain_price WHERE tldid = :id')
                ->execute(['id' => $sampleTldId]);
            $pdo->prepare('DELETE FROM domain_tld WHERE id = :id')
                ->execute(['id' => $sampleTldId]);
        }
    }

    $tldPattern = '/^(?!-)(?!.*--)[A-Z0-9-]{1,63}(?<!-)(\\.(?!-)(?!.*--)[A-Z0-9-]{1,63}(?<!-))*$/i';
    $insertTld = $pdo->prepare(
        'INSERT INTO domain_tld (tld, idn_table, secure, launch_phase_id) '
        . 'VALUES (:tld, :pattern, 0, NULL) ON DUPLICATE KEY UPDATE tld = VALUES(tld)'
    );
    $findTld = $pdo->prepare('SELECT id FROM domain_tld WHERE tld = :tld');
    $insertPrice = $pdo->prepare(
        'INSERT INTO domain_price '
        . '(tldid, registrar_id, command, m0, m12, m24, m36, m48, m60, m72, m84, m96, m108, m120) '
        . "VALUES (:tldid, NULL, :command, 0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50) "
        . 'ON DUPLICATE KEY UPDATE m12 = VALUES(m12)'
    );
    foreach ($settings['tlds'] as $tld) {
        $fqdn = '.' . $tld;
        $insertTld->execute(['tld' => $fqdn, 'pattern' => $tldPattern]);
        $findTld->execute(['tld' => $fqdn]);
        $tldId = (int) $findTld->fetchColumn();
        foreach (['create', 'renew', 'transfer'] as $command) {
            $insertPrice->execute(['tldid' => $tldId, 'command' => $command]);
        }
    }

    $stmt = $pdo->prepare(
        'INSERT INTO registrar '
        . '(name, iana_id, clid, pw, prefix, email, whois_server, rdap_server, url, '
        . 'abuse_email, abuse_phone, accountBalance, creditLimit, creditThreshold, '
        . 'thresholdType, currency, ssl_fingerprint, crdate) '
        . "VALUES (:name, :iana, :clid, :pw, :prefix, :email, :whois, "
        . ":rdap, :url, :abuse_email, :abuse_phone, "
        . "100000, 100000, 500, 'fixed', 'USD', :ssl_fingerprint, CURRENT_TIMESTAMP) "
        . 'ON DUPLICATE KEY UPDATE name = VALUES(name), iana_id = VALUES(iana_id), '
        . 'pw = VALUES(pw), prefix = VALUES(prefix), email = VALUES(email), '
        . 'whois_server = VALUES(whois_server), rdap_server = VALUES(rdap_server), '
        . 'url = VALUES(url), abuse_email = VALUES(abuse_email), '
        . 'abuse_phone = VALUES(abuse_phone), '
        . 'ssl_fingerprint = VALUES(ssl_fingerprint)'
    );
    $findRegistrar = $pdo->prepare('SELECT id FROM registrar WHERE clid = :clid');
    $deleteWhitelist = $pdo->prepare(
        'DELETE FROM registrar_whitelist WHERE registrar_id = :id'
    );
    $insertWhitelist = $pdo->prepare(
        'INSERT INTO registrar_whitelist (registrar_id, addr) VALUES (:id, :addr)'
    );
    foreach ($settings['registrars'] as $registrar) {
        $stmt->execute([
            'name' => $registrar['name'],
            'iana' => $registrar['iana_id'],
            'clid' => $registrar['clid'],
            'pw' => password_hash($registrar['password'], PASSWORD_ARGON2ID),
            'prefix' => $registrar['prefix'],
            'email' => $registrar['email'],
            'whois' => $registrar['whois'],
            'rdap' => $registrar['rdap'],
            'url' => $registrar['url'],
            'abuse_email' => $registrar['abuse_email'],
            'abuse_phone' => $registrar['abuse_phone'],
            'ssl_fingerprint' => $registrar['ssl_fingerprint'],
        ]);
        $findRegistrar->execute(['clid' => $registrar['clid']]);
        $registrarId = (int) $findRegistrar->fetchColumn();
        $deleteWhitelist->execute(['id' => $registrarId]);
        foreach ($registrar['whitelist'] as $address) {
            $insertWhitelist->execute(['id' => $registrarId, 'addr' => $address]);
        }
    }
    $pdo->commit();
} catch (Throwable $error) {
    if ($pdo->inTransaction()) {
        $pdo->rollBack();
    }
    throw $error;
}
