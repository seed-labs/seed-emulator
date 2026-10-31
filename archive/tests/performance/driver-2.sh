#!/bin/bash

set -e

cd "`dirname "$0"`"
results="`pwd`/results"

for ((i=${START}; i<=${END}; i+=${STEP})); do {
    rm -rf out

    echo "generating emulation..."
    [ "$TARGET" = "ases" ] && ./generator-2.py --ases $i --hops 10 --outdir out
    [ "$TARGET" = "hops" ] && ./generator-2.py --ases 1 --hops $i --outdir out

    this_results="$results/bench-$i-fwd-$TARGET"

    [ ! -d "$this_results" ] && mkdir "$this_results"
    pushd out

    echo "buliding emulation..."
    docker-compose build
    # bugged? stuck forever at "compose.parallel.feed_queue: Pending: set()"...
    # docker-compose up -d
    # start only 10 at a time to prevent hangs
    echo "start emulation..."
    ls | grep -Ev '.yml$|^dummies$' | xargs -n10 -exec docker-compose up -d

    echo "wait for tests..."
    sleep 500

    host_ids="`docker ps | egrep "hnode_.*_a" | cut -d\  -f1`"
    for id in $host_ids; do {
        while ! docker exec $id ls /done; do {
            echo "waiting for $id to finish tests..."
            sleep 10
        }; done

        echo "collecting results from $id..."
        docker cp "$id:/ping.txt" "$this_results/$id-ping.txt"
        docker cp "$id:/iperf-tx.txt" "$this_results/$id-iperf-tx.txt"
        docker cp "$id:/iperf-rx.txt" "$this_results/$id-iperf-rx.txt"
    }; done

    docker-compose down
    popd
}; done
