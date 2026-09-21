#!/bin/sh
set -eu

service mariadb start
service php8.5-fpm start
if [ ! -e /var/lib/loom/.seedemu-initialized ]; then
__SEED_BOOTSTRAP__
    mkdir -p /var/lib/loom
    touch /var/lib/loom/.seedemu-initialized
fi
__SEED_SOURCE_BOOTSTRAP__
service nginx start
__SEED_EPP_PROBE__

