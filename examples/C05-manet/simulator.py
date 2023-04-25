#!/usr/bin/env python3
# encoding: utf-8

import numpy as np
import json
import random
import time

def move(x,y):
    dx = random.randint(-100, 100)
    dy = random.randint(-100, 100)

    if x+dx > 1000 or x+dx < 0:
        dx *= (-1)

    if y+dy > 1000 or y+dy < 0:
        dy *= (-1)
    return x+dx, y+dy

def get_distance(x1, y1, x2, y2):
    a = np.array((x1, y1))
    b = np.array((x2, y2))

    dist = np.sqrt(np.sum(np.square(a-b)))
    return dist

for iter in range(1000):
    start = time.time()

    f = open("/home/won/master/seed-emulator/examples/C05-manet/command/node_pos.json")

    data = json.load(f)
    f.close()

    node_total = data["node_count"]
    for i in range(node_total):
        x, y = data["node_info"][i]["x"], data["node_info"][i]["y"]
        data["node_info"][i]["x"], data["node_info"][i]["y"] = move(x,y)
    for i in range(node_total):
        x1, y1 = data["node_info"][i]["x"], data["node_info"][i]["y"]
        for j in range(i+1, node_total):
            x2, y2 = data["node_info"][j]["x"], data["node_info"][j]["y"]
            data["node_info"][i]["dist"][j+1] = get_distance(x1, y1, x2, y2)

    # Serializing json
    json_object = json.dumps(data, indent=4)
    
    # Writing to sample.json
    with open("/home/won/master/seed-emulator/examples/C05-manet/command/node_pos.json", "w") as outfile:
        outfile.write(json_object)

    end = time.time()
    print((end-start)*1000,"miliseconds")
    time.sleep(1)