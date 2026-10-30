#!/bin/bash

TARGET='./target_prefix'
BGP_CONF_DIR="../01_bgp_prefix_hijacking/files/as199_include"

sudo rm -rf   "$BGP_CONF_DIR"  # Clean the folder
mkdir -p "$BGP_CONF_DIR"  # Create the folder if it does not exist

# Check if the file exists
if [ ! -f "$TARGET" ]; then
    echo "Error: File '$TARGET' not found."
    exit 1
fi

BGP_ENTRIES=''
# Read the file line by line
# IFS= prevents trimming leading/trailing whitespace from the raw line
# -r prevents backslashes from being interpreted as escape characters
# || [ -n "$line" ] ensures the last line is processed even if it lacks a newline
while IFS= read -r line || [ -n "$line" ]; do

    [[ "$line" == \#* ]] && continue   # Skip comment
    [[ -z "$line" ]] && continue       # Skip empty lines 

    # Split the line into an array
    # Unquoted $line inside parentheses triggers default word splitting (whitespace)
    elements=($line)

    # Set up bird conf's include entries; only use the first field 
    IP_PREFIX="${elements[0]}"
    BGP_ENTRY=$(cat <<EOF
protocol static {
   ipv4 { table t_bgp;  };
   route $IP_PREFIX blackhole   {
      bgp_large_community.add(LOCAL_COMM);
   };
}
EOF
   )
   BGP_CONF="$BGP_CONF_DIR"$'/'"${IP_PREFIX/\//_}".conf
   echo "$BGP_ENTRY" > "$BGP_CONF"

done < "$TARGET"

