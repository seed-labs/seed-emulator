<?php
$path = '/opt/loom/bootstrap/helper.php';
$contents = file_get_contents($path);
if ($contents === false) {
    throw new RuntimeException("Cannot read $path");
}
$replacements = [
    'return $tldMap[$last];' => "return 'generic';",
    "return \$tldMap[\$tld] ?? 'generic';" => "return 'generic';",
];
foreach ($replacements as $from => $to) {
    if (substr_count($contents, $from) !== 1) {
        throw new RuntimeException("Pinned Loom EPP selector context mismatch");
    }
    $contents = str_replace($from, $to, $contents);
}
if (file_put_contents($path, $contents) === false) {
    throw new RuntimeException("Cannot write $path");
}

