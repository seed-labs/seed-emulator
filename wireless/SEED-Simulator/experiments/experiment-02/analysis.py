#!/bin/env python3 

import re
import matplotlib.pyplot as plt

FILE_PATH = '/tmp/seedsim/tc_command/{node_id}/test_result'  # Replace with the path to your file
ITER_PATTERN = re.compile(r'''iter - (\d+): run command
current time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})
start time: (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})
iter - \d+ : elapsed time: (\d+) ms''')

def get_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            file_contents = file.read()
            return file_contents
            
    except FileNotFoundError:
        print(f"The file at '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

start_time_accuracy_list = []
elapsed_time_list = []
for node_id in range(30):
    file_contents = get_file_content(file_path=FILE_PATH.format(node_id=node_id))
    match = ITER_PATTERN.findall(file_contents)

    iter_total = len(match)

    # Variables for controlling the execution of the 'tc' command:
    # - `desired_start_time`: The intended time for the 'tc' command to be executed.
    # - `current_time`: The actual time when the 'tc' command is executed.
    # - `elapsed_time`: The duration it takes for the 'tc' command to complete execution.

    # counting occurrences when `desired_time` matches `current_time`
    start_time_accuracy = 0
    avg_elapsed_time = 0

    for iter, current_time, desired_start_time, elapsed_time in match:
        if current_time == desired_start_time:
            start_time_accuracy += 1
        
        avg_elapsed_time += int(elapsed_time)

    start_time_accuracy = start_time_accuracy/iter_total*100
    avg_elapsed_time = round(avg_elapsed_time/iter_total,2)
    start_time_accuracy_list.append(start_time_accuracy)
    elapsed_time_list.append(avg_elapsed_time)
    print("node ", node_id)
    print("start time accuracy: ", start_time_accuracy, "%")
    print("average elapsed time: ", avg_elapsed_time, "ms")


# Draw Plot
plt.subplot(2, 1, 1)

plt.ylim(0, 100+10)
plt.scatter(range(30), start_time_accuracy_list, s=10)
plt.title('[ Start Time Accuracy ]')
plt.xlabel('Node Id')
plt.ylabel('Accuracy (%)')


plt.subplot(2, 1, 2)
plt.scatter(range(30), elapsed_time_list, s=10)
plt.title('[ Average TC Command Execution Time ]')
plt.xlabel('Node Id')
plt.ylabel("Execution Time (ms)")

max_value=max(elapsed_time_list)
min_value=min(elapsed_time_list)
avg_value=round(sum(elapsed_time_list)/len(elapsed_time_list),2)

plt.text(elapsed_time_list.index(max_value), max_value + 1, f'Max: {max_value} (ms)', ha='center', va='bottom', color='red')
plt.text(elapsed_time_list.index(min_value), min_value - 1, f'Min: {min_value} (ms)', ha='center', va='top', color='blue')
plt.text(3, avg_value - 1, f'Avg: {avg_value} (ms)', ha='center', va='top', color='black')


plt.scatter([elapsed_time_list.index(max_value)], [max_value], color='red', marker='o', label='Max Value')
plt.scatter([elapsed_time_list.index(min_value)], [min_value], color='blue', marker='o', label='Min Value')

plt.tight_layout()

# Save the figure (choose a file format, such as PNG or PDF)
plt.savefig('figs/exp2-fig1.png')

# plt.show()