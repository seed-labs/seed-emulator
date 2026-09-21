<?php
$path = '/opt/loom/routes/web.php';
$contents = file_get_contents($path);
if ($contents === false) {
    throw new RuntimeException("Cannot read $path");
}
$from = "        \$db_address = 'localhost';";
$to = "        \$db_address = \$db['mysql']['host'];";
if (substr_count($contents, $from) < 1) {
    throw new RuntimeException("Pinned Loom API database context mismatch");
}
$contents = preg_replace('/^' . preg_quote($from, '/') . '$/m', $to, $contents, 1);
if (file_put_contents($path, $contents) === false) {
    throw new RuntimeException("Cannot write $path");
}

