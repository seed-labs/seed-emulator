<?php
$loomRoot = rtrim(getenv('LOOM_ROOT') ?: '/opt/loom', '/');
$edits = [
    $loomRoot . '/bootstrap/helper.php' => [
        "function getDomainConfig(\$domains, \\Pinga\\Db\\PdoDatabase \$db): array" =>
            "function isDirectRegistrationNameSupported(string \$domain, string \$tld): bool\n"
            . "{\n"
            . "    \$asciiDomain = idn_to_ascii(\$domain, IDNA_DEFAULT, INTL_IDNA_VARIANT_UTS46);\n"
            . "    if (\$asciiDomain === false) {\n"
            . "        return false;\n"
            . "    }\n\n"
            . "    \$normalizedDomain = strtolower(trim(\$asciiDomain, \". \\t\\n\\r\\0\\x0B\"));\n"
            . "    \$normalizedTld = strtolower(trim(\$tld, \". \\t\\n\\r\\0\\x0B\"));\n"
            . "    if (\$normalizedDomain === '' || \$normalizedTld === '') {\n"
            . "        return false;\n"
            . "    }\n\n"
            . "    \$suffix = '.' . \$normalizedTld;\n"
            . "    if (!str_ends_with(\$normalizedDomain, \$suffix)) {\n"
            . "        return false;\n"
            . "    }\n\n"
            . "    \$registrableLabel = substr(\$normalizedDomain, 0, -strlen(\$suffix));\n"
            . "    return \$registrableLabel !== '' && !str_contains(\$registrableLabel, '.');\n"
            . "}\n\n"
            . "function getDomainConfig(\$domains, \\Pinga\\Db\\PdoDatabase \$db): array",
    ],
    $loomRoot . '/app/Controllers/SparkController.php' => [
        "        \$registryType = getRegistryExtensionByTld('.'.\$domainData[0]['tld']);" =>
            "        \$configuredTld = (string) \$domainData[0]['tld'];\n"
            . "        if (!isDirectRegistrationNameSupported(\$domains[0], \$configuredTld)) {\n"
            . "            \$response->getBody()->write(json_encode([\n"
            . "                'success' => false,\n"
            . "                'message' => 'Only domains directly under the configured TLD can be registered. Register the parent domain and create deeper names as DNS records.',\n"
            . "            ], JSON_UNESCAPED_UNICODE));\n\n"
            . "            return \$response\n"
            . "                ->withHeader('Content-Type', 'application/json; charset=UTF-8')\n"
            . "                ->withStatus(422);\n"
            . "        }\n\n"
            . "        \$registryType = getRegistryExtensionByTld('.'.\$domainData[0]['tld']);",
    ],
    $loomRoot . '/app/Controllers/OrdersController.php' => [
        "            \$domainName = \$_SESSION['domains_to_create'][0];\n            \$amount = \$_SESSION['domains_to_register_price'][0];" =>
            "            \$domainName = \$_SESSION['domains_to_create'][0];\n"
            . "            \$domainConfig = getDomainConfig([\$domainName], \$db);\n"
            . "            \$configuredTld = (string) (\$domainConfig[0]['tld'] ?? '');\n"
            . "            if (!isDirectRegistrationNameSupported(\$domainName, \$configuredTld)) {\n"
            . "                \$this->container->get('flash')->addMessage(\n"
            . "                    'error',\n"
            . "                    'Only domains directly under the configured TLD can be registered. Register the parent domain and create deeper names as DNS records.'\n"
            . "                );\n"
            . "                unset(\$_SESSION['domains_to_create']);\n"
            . "                unset(\$_SESSION['domains_to_register_price']);\n"
            . "                return \$response->withHeader('Location', '/orders')->withStatus(302);\n"
            . "            }\n\n"
            . "            \$amount = \$_SESSION['domains_to_register_price'][0];",
    ],
];

foreach ($edits as $path => $replacements) {
    $contents = file_get_contents($path);
    if ($contents === false) {
        throw new RuntimeException("Cannot read $path");
    }
    foreach ($replacements as $from => $to) {
        if (substr_count($contents, $from) !== 1) {
            throw new RuntimeException("Pinned Loom registration-boundary patch context mismatch in $path");
        }
        $contents = str_replace($from, $to, $contents);
    }
    if (file_put_contents($path, $contents) === false) {
        throw new RuntimeException("Cannot write $path");
    }
}
