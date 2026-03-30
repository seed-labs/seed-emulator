#!/usr/bin/env bash

# Disable Docker BuildKit to avoid multi-thread conflicts
export DOCKER_BUILDKIT=0

# ===============================================
# Batch docker-compose build script
# Default batch size: 50 services per batch
# Includes logging, retry on failure, and detailed output
# ===============================================

BATCH_SIZE=50
LOG_FILE="batch_compose_build.log"
COMPOSE_FILE="./output/docker-compose.yml"

echo "===== Executing docker compose build in batches =====" | tee "$LOG_FILE"
echo "Batch size: $BATCH_SIZE" | tee -a "$LOG_FILE"
echo "Start time: $(date)" | tee -a "$LOG_FILE"

if [ ! -f "$COMPOSE_FILE" ]; then
    echo "No compose file at $COMPOSE_FILE. Exiting script." | tee -a "$LOG_FILE"
    exit 1
fi
services=($(docker compose -f "$COMPOSE_FILE" config --services))
total=${#services[@]}
echo "Total number of services: $total" | tee -a "$LOG_FILE"

if [ $total -eq 0 ]; then
    echo "? No services found in $COMPOSE_FILE. Exiting script." | tee -a "$LOG_FILE"
    exit 1
fi

batch_count=0

# ===============================================
# Batch build
for ((i=0; i<total; i+=BATCH_SIZE)); do
    batch_count=$((batch_count + 1))
    batch_services=("${services[@]:i:BATCH_SIZE}")

    echo "" | tee -a "$LOG_FILE"
    echo "=== Starting build batch $batch_count (index $i ~ $((i + BATCH_SIZE - 1))) ===" | tee -a "$LOG_FILE"

    # Print names of services in this batch
    printf "%s\n" "${batch_services[@]}" | tee -a "$LOG_FILE"

    docker compose -f "$COMPOSE_FILE" build "${batch_services[@]}"
    status=$?

    # Retry once if failed
    if [ $status -ne 0 ]; then
        echo "??  Batch $batch_count build failed. Retrying in 3 seconds..." | tee -a "$LOG_FILE"
        sleep 3

        docker compose -f "$COMPOSE_FILE" build "${batch_services[@]}"
        retry_status=$?

        if [ $retry_status -ne 0 ]; then
            echo "? Batch $batch_count retry failed. Please check logs manually." | tee -a "$LOG_FILE"
        else
            echo "? Batch $batch_count retry succeeded." | tee -a "$LOG_FILE"
        fi
    else
        echo "? Batch $batch_count build succeeded." | tee -a "$LOG_FILE"
    fi
done

echo "" | tee -a "$LOG_FILE"
echo "?? All batch builds completed. Total services built: $total" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE"
