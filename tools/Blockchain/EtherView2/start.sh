#!/bin/sh
set -e

if [ "$DEFAULT_ROUTE" ]; then
    ip rou del default 2> /dev/null
    ip route add default via $DEFAULT_ROUTE dev eth0
fi

if [ ! -d "/var/lib/mysql/mysql" ]; then
    mysqld --initialize-insecure
fi

mysqld_safe &
until mysqladmin ping -h127.0.0.1 --silent; do
    echo "Waiting for MySQL..."
    sleep 1
done

DB_NAME="${MYSQL_DATABASE:-eth_monitor}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-123456}"
mysql -uroot -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASSWORD}'; FLUSH PRIVILEGES;"
mysql -uroot $( [ -n "$MYSQL_ROOT_PASSWORD" ] && echo "-p$MYSQL_ROOT_PASSWORD" ) -e \
    "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

while true; do
    FLASK_APP=server flask run --host=0.0.0.0 --port=5000
done
