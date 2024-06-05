#!/bin/bash
DIRECTORY="./jobs/"
ORACLE_ADDRESS_FILE="./info/oracle_contract_address.txt"
TIMEOUT=1000
SLEEP_DURATION=10

# Change the work folder to where the program is
cd "$(dirname "$0")"

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory $DIRECTORY does not exist."
    exit 1
fi

ELAPSED_TIME=0
while [ ! -f "$ORACLE_ADDRESS_FILE" ] && [ $ELAPSED_TIME -lt $TIMEOUT ]; do
    sleep $SLEEP_DURATION
    ELAPSED_TIME=$((ELAPSED_TIME + SLEEP_DURATION))
    echo "Waiting for Oracle address file..."
done

if [ ! -f "$ORACLE_ADDRESS_FILE" ]; then
    echo "Error: Oracle address file $ORACLE_ADDRESS_FILE does not exist after $TIMEOUT seconds."
    exit 1
fi

ORACLE_RELATION_RESPONSE=$(<"$ORACLE_ADDRESS_FILE")

if [ ! -d "$DIRECTORY" ]; then
        echo "Error: Directory does not exist."
        exit 1
    fi

    find "$DIRECTORY" -type f -name '*.toml' -print0 | while IFS= read -r -d $'\0' file; do
        sed -i "s/oracle_contract_address/$ORACLE_RELATION_RESPONSE/g" "$file"
        echo "Updated oracle contract address in $file"
    done

    echo "All TOML files have been updated."

chainlink admin login -f ./password.txt

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory does not exist."
    exit 1
fi

for toml_file in "$DIRECTORY"*.toml; do
    if [ ! -f "$toml_file" ]; then
        echo "No TOML files found in the directory."
        continue
    fi

    echo "Creating Chainlink job from $toml_file..."
    chainlink jobs create "$toml_file"

    echo "Job created from $toml_file"
done

echo "All jobs have been created."
