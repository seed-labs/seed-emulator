TC_RUNNER_SCRIPT = '''#!/bin/bash

line=$(cat /setting/info.txt)
iteration=$(cut -d '-' -f1 <<< $line)
iter_duration=$(cut -d '-' -f2 <<< $line)
# Define the start time with the format HH:MM:SS
start_time=$(cut -d '-' -f3 <<< $line)
sleep_duration=$(cut -d '-' -f4 <<< $line)

# Set the boolean variable
log_enabled={isLogEnabled}

echo "line: $line" > /tc_command/test_result
echo "iteration: $iteration" >> /tc_command/test_result
echo "iter_duration: $iter_duration" >> /tc_command/test_result
echo "start_time: $start_time" >> /tc_command/test_result

# Get the current time in the same format
current_time=$(date +'%H:%M:%S')

# Calculate the time difference in seconds
current_time_in_second=$(date -d "$current_time" +'%s')
start_time_in_second=$(date -d "$start_time" +'%s')

start_time_array=()
for ((i=0; i<$iteration; i++)); do
  start_time_array+=("$start_time_in_second")
  start_time_in_second=$((start_time_in_second + iter_duration))
done

sleep_seconds=$((start_time_in_second - current_time_in_second))

# Ensure the sleep time is non-negative
iter=0
current_time=$(date +%s)

echo "current time: $(date -d @$current_time +"%Y-%m-%d %H:%M:%S")" >> /tc_command/test_result
echo "desired start time: $(date -d @${{start_time_array[$iter]}} +"%Y-%m-%d %H:%M:%S")" >> /tc_command/test_result

echo "tc rule log"> /tc_command/tc_rule_log.txt
mkdir -p /tc_command/pingLog
mkdir -p /tc_command/routeLog
rm -rf /tc_command/pingLog/*
rm -rf /tc_command/routeLog/*

if [ $current_time -gt ${{start_time_array[$iter]}} ]; then
    echo "Desired time has already passed." >> /tc_command/test_result
else
    echo "Task started at $desired_time" >> /tc_command/test_result
    while [ $iter -lt $iteration ]; do
        current_time=$(date +%s)
        if [ $current_time -ge ${{start_time_array[$iter]}} ]; then
            # Get the start time in milliseconds
            start_time=$(date +%s%N | cut -b1-13)
            /tc_command/tc_command_$iter
            # Get the end time in milliseconds
            end_time=$(date +%s%N | cut -b1-13)
            echo "iter - $iter: run command" >> /tc_command/test_result
            echo "current time: $(date -d @$current_time +"%Y-%m-%d %H:%M:%S")" >> /tc_command/test_result
            echo "start time: $(date -d @${{start_time_array[$iter]}} +"%Y-%m-%d %H:%M:%S")" >> /tc_command/test_result
            # Calculate the elapsed time in milliseconds
            elapsed_time=$((end_time - start_time))

            # Display the elapsed time
            echo "iter - $iter : elapsed time: ${{elapsed_time}} ms" >> /tc_command/test_result

            # Check if log_enabled is true
            if [ "$log_enabled" = true ]; then
                # Log tc rule
                echo "iter - $iter">> /tc_command/tc_rule_log.txt
                tc qdisc show | grep loss >> /tc_command/tc_rule_log.txt

                echo "sleep until log routing table and ping result"
                sleep {ping_time}
                
                # Log routing table
                ip route >> /tc_command/routeLog/log_$iter.txt

                #Ping route log
                ping -R 10.0.0.129 -D -c 2 -i 0.5 >> /tc_command/pingLog/log_$iter.txt 2>&1 &
            else
                echo "Do nothing if log_enabled is false."
            fi

            iter=$((iter + 1))
        else
            echo "iter - $iter: $sleep_duration" >> /tc_command/test_result
            echo $(date -d @$current_time +"%Y-%m-%d %H:%M:%S") >> /tc_command/test_result
            echo $(date -d @${{start_time_array[$iter]}} +"%Y-%m-%d %H:%M:%S") >> /tc_command/test_result
            sleep $sleep_duration
        fi
    done
fi
'''

TC_SCRIPT = '''\
#!/bin/bash

{tc_command}
'''
