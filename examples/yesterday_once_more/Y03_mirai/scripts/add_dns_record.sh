#!/bin/sh

# This script automates the process of adding a new master zone to a BIND9 server.
# Usage: ./add_dns_record.sh <domain> [ip_address]
# Examples:
#   ./add_dns_record.sh killswitch.com
#   ./add_dns_record.sh my-site.com 10.20.30.40

# Configuration
BIND_CONFIG_DIR="/etc/bind"
NAMED_CONF_LOCAL="${BIND_CONFIG_DIR}/named.conf.local"

# Parameter Handling
DOMAIN=$1
IP_ADDRESS=${2:-"1.1.1.1"} # default to "1.1.1.1"

if [ -z "$DOMAIN" ]; then
  echo "Error: You must provide a domain name as the first argument."
  echo "Usage: $0 <domain> [ip_address]"
  exit 1
fi

ZONE_FILE="${BIND_CONFIG_DIR}/db.${DOMAIN}"

echo "--- Starting to add DNS record for domain '${DOMAIN}' ---"
echo "  - IP Address will be: ${IP_ADDRESS}"
echo "  - BIND config file:   ${NAMED_CONF_LOCAL}"
echo "  - Zone data file:     ${ZONE_FILE}"
echo ""

# Check if the zone already exists
if grep -q "zone \"${DOMAIN}\"" "$NAMED_CONF_LOCAL"; then
  echo "Warning: A zone definition for domain '${DOMAIN}' already exists in ${NAMED_CONF_LOCAL}."
  echo "Operation cancelled."
  exit 1
fi

echo "1. Appending zone definition to ${NAMED_CONF_LOCAL}..."
cat <<EOF >> "$NAMED_CONF_LOCAL"

// Automatically added by add_dns_record.sh on $(date)
zone "${DOMAIN}" {
    type master;
    file "${ZONE_FILE}";
};
EOF
echo "   ...Done."
echo ""

echo "2. Creating new zone data file ${ZONE_FILE}..."
cat <<EOF > "$ZONE_FILE"
\$TTL    60
@       IN      SOA     ns1.${DOMAIN}. admin.${DOMAIN}. (
                          1         ; Serial
                          604800    ; Refresh
                          86400     ; Retry
                          2419200   ; Expire
                          60 )      ; Negative Cache TTL
;
@       IN      NS      ns1.${DOMAIN}.
@       IN      A       ${IP_ADDRESS}
ns1     IN      A       ${IP_ADDRESS}
EOF
echo "   ...Done."
echo ""

echo "3. Checking BIND configuration syntax..."
named-checkconf
if [ $? -ne 0 ]; then
    echo "Error: BIND configuration check failed! Please check ${NAMED_CONF_LOCAL} manually."
    exit 1
fi
echo "   ...Syntax OK."
echo ""

echo "4. Reloading BIND9 service to apply changes..."
rndc reload
echo "   ...Service reloaded."
echo ""

echo "--- Success! ---"
echo "Domain '${DOMAIN}' has been successfully pointed to IP Address '${IP_ADDRESS}'."
echo "You can now try to verify the change with the following command:"
echo "dig ${DOMAIN} @localhost"