#!/bin/env python3 

from seedsim import *
import threading
import time

ITERATION = 30

simTool = SimTool()

# Event to signal when thread 2 is done
thread2_done_event = threading.Event()

def thread_function_1():
    routes = None
    while not thread2_done_event.is_set():
        simTool.calc_routes_and_loss()
        _, tmp_routes = simTool.get_route_info(src=9, dst=29)
        if routes == tmp_routes:
            print("routes not changed.")
        else:
            simTool.print_route_info(src=9, dst=29)
            routes = tmp_routes
        time.sleep(3)

    print("Thread 1 is stopping.")

def thread_function_2():
    for i in range(21, 26):
        print("Move to iter at {}".format(i))
        simTool.move_to_iter_at(iter=i)
        time.sleep(12)

    # Set the event to signal thread 1 to stop
    thread2_done_event.set()
    print("Thread 2 is done.")

# Create two thread objects
thread_1 = threading.Thread(target=thread_function_1)
thread_2 = threading.Thread(target=thread_function_2)

# Start the threads
thread_1.start()
thread_2.start()

# Wait for both threads to finish
thread_1.join()
thread_2.join()

print("Both threads have finished.")





# simTool.move_to_iter_at(iter=17)
# sleep(10)
# simTool.calc_routes_and_loss()
# simTool.print_route_info(src=9, dst=22)
# dst, route, loss = simTool.get_route_info(src=0, dst=22)

# simTool.move_to_iter_at(iter=20)

# i=0
# while True:
#     print("sleep ", i)
#     i+=1
#     sleep(1)
#     simTool.calc_routes_and_loss()
#     tmp_dst, tmp_route, tmp_loss = simTool.get_route_info(src=0, dst=22)
#     if tmp_route != route:
#         simTool.print_route_info(src=9, dst=22)
        
# #         break
# # sleep(10)
# # simTool.calc_routes_and_loss()
# # simTool.print_route_info(src=9, dst=22)


