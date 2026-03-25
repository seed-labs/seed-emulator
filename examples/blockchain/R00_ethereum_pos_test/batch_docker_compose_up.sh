#!/usr/bin/env bash

# Disable Docker BuildKit
export DOCKER_BUILDKIT=0

# ==============================
# Batch start docker-compose services
# Default batch size is 50, can be adjusted via BATCH_SIZE
# ==============================

BATCH_SIZE=50
LOG_FILE="batch_compose_up.log"
COMPOSE_FILE="./output/docker-compose.yml"

echo "===== Batch starting docker compose services =====" | tee "$LOG_FILE"
echo "Batch size: $BATCH_SIZE" | tee -a "$LOG_FILE"
echo "Start time: $(date)" | tee -a "$LOG_FILE"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "No compose file at $COMPOSE_FILE, exiting" | tee -a "$LOG_FILE"
    exit 1
fi
services=($(docker compose -f "$COMPOSE_FILE" config --services))
total=${#services[@]}
echo "Total services: $total" | tee -a "$LOG_FILE"

if [ $total -eq 0 ]; then
    echo "? No services found in $COMPOSE_FILE, exiting" | tee -a "$LOG_FILE"
    exit 1
fi

batch_count=0

# Batch start loop
for ((i=0; i<total; i+=BATCH_SIZE)); do
    batch_count=$((batch_count + 1))
    batch_services=("${services[@]:i:BATCH_SIZE}")

    echo "" | tee -a "$LOG_FILE"
    echo "=== Starting batch $batch_count (index $i ~ $((i + BATCH_SIZE - 1))) ===" | tee -a "$LOG_FILE"

    # Print service names in this batch
    printf "%s\n" "${batch_services[@]}" | tee -a "$LOG_FILE"

    docker compose -f "$COMPOSE_FILE" up -d "${batch_services[@]}"
    status=$?

    # Retry once if failed
    if [ $status -ne 0 ]; then
        echo "??  Batch $batch_count failed, retrying in 3 seconds..." | tee -a "$LOG_FILE"
        sleep 3
        docker compose -f "$COMPOSE_FILE" up -d "${batch_services[@]}"
        retry_status=$?

        if [ $retry_status -ne 0 ]; then
            echo "? Batch $batch_count retry still failed. Check log for details." | tee -a "$LOG_FILE"
        else
            echo "? Batch $batch_count retry succeeded." | tee -a "$LOG_FILE"
        fi
    else
        echo "? Batch $batch_count started successfully" | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
echo "?? All batches completed. Total services started: $total" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE"
