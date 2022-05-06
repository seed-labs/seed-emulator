 (ls | grep -Ev '.yml$|^dummies$|^eth-states|^lazy_start' | xargs -n10 -exec docker-compose up -d) > /dev/pts/0
