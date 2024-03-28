#!/bin/env python3 

import pandas as pd

NODE_TOTAL  = 30
ITERATION   = 10

df = pd.read_csv('tc_applied_rule.csv')
df['next_hop'] = 0


# Open a file for reading
for tx_node_id in range(NODE_TOTAL):
    for iter in range(ITERATION):
        with open('/tmp/seedsim/tc_command/{}/routeLog/log_{}.txt'.format(tx_node_id, iter), 'r') as file:
            # Read the entire file
            content = file.read()

        for row in content.split('\n'):
            if len(row) > 0 and row.split(' ')[1] == 'via':
                rx_node_id = int(row.split(' ')[0].split('.')[-1])%100
                next_hop = int(row.split(' ')[2].split('.')[-1])%100
                print(rx_node_id, next_hop)
                # Update the cell
                condition = (df['tx_node_id'] == tx_node_id) & (df['Iter'] == iter) & (df['rx_node_id'] == rx_node_id)
                df.loc[condition, 'next_hop'] = next_hop

df.to_csv('next_hop.csv', index=False)