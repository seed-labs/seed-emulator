#!/bin/sh
set -eu

service mariadb start
service redis-server start
until mariadb-admin ping --silent; do sleep 1; done
mariadb < /opt/seedemu/namingo/init.sql

if ! mariadb -Nse "SELECT 1 FROM information_schema.tables WHERE table_schema='__SEED_DATABASE__' AND table_name='users'" | grep -q 1; then
    mariadb < /opt/registry/database/registry.mariadb.sql
fi

/usr/bin/php8.5 /opt/seedemu/namingo/bootstrap.php
mkdir -p /var/log/namingo /run /var/lib/bind /opt/seedemu/namingo/tls

if [ ! -s /opt/seedemu/namingo/tls/epp.crt ] || [ ! -s /opt/seedemu/namingo/tls/epp.key ]; then
    openssl req -x509 -newkey rsa:3072 -sha256 -nodes -days 14 \
        -subj '/CN=__SEED_EPP_HOST__' -addext 'subjectAltName=DNS:__SEED_EPP_SAN_HOST__' \
        -keyout /opt/seedemu/namingo/tls/epp.key \
        -out /opt/seedemu/namingo/tls/epp.crt
fi
chmod 600 /opt/seedemu/namingo/tls/epp.key

__SEED_COMMANDS__
