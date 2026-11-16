#!/bin/bash

SAMPLE_COUNT='100'

set -e

cd "`dirname "$0"`"
results="`pwd`/results"

[ ! -d "$results" ] && mkdir "$results"

function collect {
    for j in `seq 1 $SAMPLE_COUNT`; do {
        now="`date +%s`"
        echo "[$now] snapshotting cpu/mem info..."
        cat /proc/stat > "$this_results/stat-$now.txt"
        cat /proc/meminfo > "$this_results/meminfo-$now.txt"
        sleep 1
    }; done
}

for ((i=${START}; i<=${END}; i+=${STEP})); do {
    rm -rf out

    echo "generating emulation..."
    [ "$TARGET" = "ases" ] && \
        ./generator-1.py --ases $i --ixs 5 --routers 1 --hosts 0 --outdir out --yes
    [ "$TARGET" = "routers" ] && \
        ./generator-1.py --ases 10 --ixs 5 --routers $i --hosts 0 --outdir out --yes
    [ "$TARGET" = "hosts" ] && \
        ./generator-1.py --ases 10 --ixs 5 --routers 1 --hosts $i --outdir out --yes
    this_results="$results/bench-$i-$TARGET"
    [ ! -d "$this_results" ] && mkdir "$this_results"
    pushd out

    echo "buliding emulation..."
    docker-compose build
    # bugged? stuck forever at "compose.parallel.feed_queue: Pending: set()"...
    # docker-compose up -d 
    
    # start only 10 at a time to prevent hangs
    echo "start emulation..."
    ls | grep -Ev '.yml$|^dummies$' | xargs -n10 -exec docker-compose up -d

    echo "waiting 300s for ospf/bgp, etc..."
    sleep 300
    collect

    docker-compose down
    popd
}; done
