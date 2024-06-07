#!/bin/bash

# Define the URL of the server to connect to
SERVER_URL="http://{address}:{port}"

# Number of attempts
ATTEMPTS={max_attempts}

# Initialize a counter
count=0

# Loop until connection is successful or maximum attempts reached
while [ $count -lt $ATTEMPTS ]; do
    # Perform an HTTP GET request to the server and check the response status code
    status_code=$(curl -s -o /dev/null -w "%{{http_code}}" "$SERVER_URL")

    # Check if the server is accessible (HTTP status code 200)
    if [ "$status_code" -eq 200 ]; then
        echo "Connection successful."
        {fund_command}
        exit 0  # Exit with success status
    else
        echo "Attempt $((count+1)): Connection failed (HTTP status code $status_code). Retrying..."
        count=$((count+1))  # Increment the counter
        sleep 10  # Wait for 10 seconds before retrying
    fi
done

# If maximum attempts reached and connection is still unsuccessful
echo "Connection failed after $ATTEMPTS attempts."
exit 1  # Exit with error status
