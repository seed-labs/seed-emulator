<?php
$edits = [
    '/opt/loom/app/Controllers/OrdersController.php' => [
        "            \$nameservers = \$data['nameserver'] ?? [];" =>
            "            \$nameservers = \$data['nameserver'] ?? [];\n"
            . "            \$nameserverAddresses = \$data['nameserver_ipv4'] ?? [];",
        "                    'nameservers' => array_values(\$nameservers)," =>
            "                    'nameservers' => array_values(\$nameservers),\n"
            . "                    'nameserver_addresses' => array_values(\$nameserverAddresses),",
    ],
    '/opt/loom/app/Services/Provisioning/DomainProvisioner.php' => [
        "                    foreach (\$nameservers as \$host) {\n"
            . "                        // Registries commonly return \"already exists\" during a retry;\n"
            . "                        // preserve the previous best-effort host creation behavior.\n"
            . "                        \$epp->hostCreate(['hostname' => strtolower(\$host)]);\n"
            . "                    }" =>
            "                    \$addresses = is_array(\$serviceData['nameserver_addresses'] ?? null)\n"
            . "                        ? array_values(\$serviceData['nameserver_addresses']) : [];\n"
            . "                    \$pendingNameservers = [];\n"
            . "                    foreach (\$nameservers as \$index => \$host) {\n"
            . "                        \$address = trim((string)(\$addresses[\$index] ?? ''));\n"
            . "                        \$pendingNameservers[] = [\n"
            . "                            'hostname' => strtolower(\$host),\n"
            . "                            'ipaddress' => \$address,\n"
            . "                        ];\n"
            . "                    }\n"
            . "                    // Namingo requires the superordinate domain before in-bailiwick hosts.\n"
            . "                    \$domainParams['nss'] = [];",
        "            if (\$error !== null) {\n"
            . "                throw new \\RuntimeException('DomainCreate Error: ' . \$error);\n"
            . "            }" =>
            "            if (\$error !== null) {\n"
            . "                throw new \\RuntimeException('DomainCreate Error: ' . \$error);\n"
            . "            }\n"
            . "\n"
            . "            if (!empty(\$pendingNameservers)) {\n"
            . "                \$update = ['domainname' => \$domainName];\n"
            . "                foreach (\$pendingNameservers as \$index => \$host) {\n"
            . "                    \$hostCreate = \$epp->hostCreate(\$host);\n"
            . "                    \$hostError = \$this->responseError(\$hostCreate);\n"
            . "                    if (\$hostError !== null) {\n"
            . "                        throw new \\RuntimeException('HostCreate Error: ' . \$hostError);\n"
            . "                    }\n"
            . "                    \$update['ns' . (\$index + 1)] = \$host['hostname'];\n"
            . "                }\n"
            . "                \$domainUpdate = \$epp->domainUpdateNS(\$update);\n"
            . "                \$updateError = \$this->responseError(\$domainUpdate);\n"
            . "                if (\$updateError !== null) {\n"
            . "                    throw new \\RuntimeException('DomainUpdateNS Error: ' . \$updateError);\n"
            . "                }\n"
            . "            }",
    ],
];
foreach ($edits as $path => $replacements) {
    $contents = file_get_contents($path);
    if ($contents === false) {
        throw new RuntimeException("Cannot read $path");
    }
    foreach ($replacements as $from => $to) {
        if (substr_count($contents, $from) !== 1) {
            throw new RuntimeException("Pinned Loom glue patch context mismatch in $path");
        }
        $contents = str_replace($from, $to, $contents);
    }
    if (file_put_contents($path, $contents) === false) {
        throw new RuntimeException("Cannot write $path");
    }
}

