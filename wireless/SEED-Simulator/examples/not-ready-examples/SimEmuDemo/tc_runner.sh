#!/bin/bash

line=$(cat /tmp/seedsim/setting/info.txt)
iteration=$(cut -d '-' -f1 <<< $line)
iter_duration=$(cut -d '-' -f2 <<< $line)
sleep_duration=$(cut -d '-' -f4 <<< $line)

start_time_in_second=$(($(date +%s) +10))
start_time=$(date -u -d "@$start_time_in_second" +"%T")

echo "$iteration-$iter_duration-$start_time-$sleep_duration" > /tmp/seedsim/setting/info.txt

start=0
end=$(docker ps | grep Router | wc -l)
for (( node=$start; node<$end; node++ ))
do
	container=$(docker ps | grep "Router_$node-" | awk '{print $1}')
	docker exec -t -w / $container bash /tc_runner.sh &
	echo "run command on $container"
done

./visualization.py &
