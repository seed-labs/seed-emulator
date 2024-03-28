#!/usr/bin/env python3
# encoding: utf-8

import pandas as pd
import numpy as np
from pathlib import Path

TC_RUNNER_SCRIPT = '''#!/bin/bash

line=$(cat /setting/info.txt)
iteration=$(cut -d '-' -f1 <<< $line)
# Define the start time with the format HH:MM:SS
start_time=$(cut -d '-' -f2 <<< $line)
sleep_duration=$(cut -d '-' -f3 <<< $line)

echo "line: $line" > test_result
echo "iteration: $iteration" >> test_result
echo "start_time: $start_time" >> test_result

# Get the current time in the same format
current_time=$(date +'%H:%M:%S')

# Calculate the time difference in seconds
current_time_in_second=$(date -d "$current_time" +'%s')
start_time_in_second=$(date -d "$start_time" +'%s')

start_time_array=()
for ((i=0; i<$iteration; i++)); do
  start_time_array+=("$start_time_in_second")
  start_time_in_second=$((start_time_in_second + 1))
done

sleep_seconds=$((start_time_in_second - current_time_in_second))

# Ensure the sleep time is non-negative
iter=0
current_time=$(date +%s)

echo "current time: $(date -d @$current_time +"%Y-%m-%d %H:%M:%S")" >> test_result
echo "desired start time: $(date -d @${start_time_array[$iter]} +"%Y-%m-%d %H:%M:%S")" >> test_result

echo "tc rule log">tc_rule_log.txt
mkdir pingLog

if [ $current_time -gt ${start_time_array[$iter]} ]; then
    echo "Desired time has already passed." >> test_result
else
    echo "Task started at $desired_time" >> test_result
    while [ $iter -lt $iteration ]; do
        current_time=$(date +%s)
        if [ $current_time -ge ${start_time_array[$iter]} ]; then
            # Get the start time in milliseconds
            start_time=$(date +%s%N | cut -b1-13)
            /tc_command/tc_command_$iter
            # Get the end time in milliseconds
            end_time=$(date +%s%N | cut -b1-13)
            echo "iter - $iter: run command" >> test_result
            echo "current time: $(date -d @$current_time +"%Y-%m-%d %H:%M:%S")" >> test_result
            echo "start time: $(date -d @${start_time_array[$iter]} +"%Y-%m-%d %H:%M:%S")" >> test_result
            # Calculate the elapsed time in milliseconds
            elapsed_time=$((end_time - start_time))

            # Display the elapsed time
            echo "iter - $iter : elapsed time: ${elapsed_time} ms" >> test_result

            # Log tc rule
            echo "iter - $iter">> tc_rule_log.txt
            tc qdisc show | grep loss >> tc_rule_log.txt

            # Ping route log
            ping -R 10.0.0.129 -D -c 10 -i 0.05 >> /pingLog/log_$iter.txt 2>&1 &

            iter=$((iter + 1))
        else
            echo "iter - $iter: $sleep_duration" >> test_result
            echo $(date -d @$current_time +"%Y-%m-%d %H:%M:%S") >> test_result
            echo $(date -d @${start_time_array[$iter]} +"%Y-%m-%d %H:%M:%S") >> test_result
            sleep $sleep_duration
        fi
    done
fi
'''

TC_SCRIPT = '''\
#!/bin/bash

{tc_command}
'''
ITERATION=100
SLEEPDURATION=0.1
NODETOTAL = 50

directory_path = '/tmp/seedsim/setting'
directory = Path(directory_path)
if not directory.exists():
    directory.mkdir(parents=True)

with open('/tmp/seedsim/setting/info.txt', 'w') as file:
    file.write("{}-start_time-{}".format(ITERATION, SLEEPDURATION))

with open('/tmp/seedsim/tc_runner.sh', 'w') as file:
    file.write(TC_RUNNER_SCRIPT)

df = pd.read_csv('/tmp/seedsim/siminfo/siminfo.csv', delimiter=' ')
df['tc_command'] = 'tc qdisc replace dev ifb0 parent 1:1' + df['rx_node_id'].astype(str) + ' handle 1'+ df['rx_node_id'].astype(str) + ': netem delay ' + df['Delay'].astype(str) + 'us loss ' + df['LossRate'].astype(str) + '%'

for iter in range(ITERATION):
    for node_id in range(NODETOTAL):
        a = df[(df['Iter']==iter) & (df['tx_node_id']==node_id)]
        tc_cmd = np.array2string(a['tc_command'].to_numpy(), separator=';').replace('[','').replace(']', '').replace("'", "")
        
        directory_path = '/tmp/seedsim/tc_command/{node_id}'.format(node_id=node_id)
        directory = Path(directory_path)
        if not directory.exists():
            directory.mkdir(parents=True)

        with open('/tmp/seedsim/tc_command/{}/tc_command_{}'.format(node_id, iter), 'w') as file:
            file.write(TC_SCRIPT.format(tc_command=tc_cmd))