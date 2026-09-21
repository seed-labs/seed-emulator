<?php
$files = [
    '/opt/registrar/whois/src/WHOIS/LOOM.php' => 2,
    '/opt/registrar/rdap/src/RDAP/LOOM.php' => 3,
];
foreach ($files as $path => $expected) {
    $contents = file_get_contents($path);
    if ($contents === false || substr_count($contents, 'service_type') !== $expected) {
        throw new RuntimeException("Pinned Namingo Loom adapter context mismatch: {$path}");
    }
    $contents = str_replace('service_type', 'type', $contents);
    if (file_put_contents($path, $contents) === false) {
        throw new RuntimeException("Cannot update Namingo Loom adapter: {$path}");
    }
}

