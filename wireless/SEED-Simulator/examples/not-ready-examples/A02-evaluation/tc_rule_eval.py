#!/bin/env python3 

import pandas as pd

# Create an empty DataFrame
# df = pd.DataFrame(columns=['Iter', 'tx_node_id', 'rx_node_id', 'LossRate'])

# NODE_TOTAL  = 30
# ITERATION   = 10
# i=0
# # Generate dummy rows
# for iter in range(ITERATION):  # values 0 to 10 (inclusive)
#     for tx_node_id in range(NODE_TOTAL):  # values 0 to 10 (inclusive)
#         for rx_node_id in range(tx_node_id+1, NODE_TOTAL):
#             df.loc[i] = {'Iter': iter, 'tx_node_id': tx_node_id, 'rx_node_id':rx_node_id, 'LossRate':0.0}
#             i=i+1

# # Save the DataFrame to a CSV file
# df.to_csv('tc_rule_dummy.csv', index=False)

# csv_file_path = "tc_rule_dummy.csv"
# df = pd.read_csv(csv_file_path, sep=',')  # Use '\t' for tab-separated values

# # print(content.split('iter')[1])
# for tx_node_id in range(NODE_TOTAL):
#     # Open a file for reading
#     with open('/tmp/seedsim/tc_command/{}/tc_rule_log.txt'.format(tx_node_id), 'r') as file:
#         # Read the entire file
#         content = file.read()
#     for iter, tc_rules in enumerate(content.split('iter')[1:]):
#         for tc_rule in tc_rules.split('\n')[1:]:
#             if (len(tc_rule)>0):
#                 rx_id = int(tc_rule.split(' ')[2].replace(":", ""))
#                 if rx_id > 100:
#                     rx_id = rx_id%100
#                 elif rx_id > 10:
#                     rx_id = rx_id%10
#                 loss = float(tc_rule.split(' ')[-1].replace("%", ""))
#                 # print(iter, tx_node_id, rx_id, loss)
#                 # Update the cell
#                 condition = (df['tx_node_id'] == tx_node_id) & (df['Iter'] == iter) & (df['rx_node_id'] == rx_id)
#                 df.loc[condition, 'LossRate'] = loss

# df.to_csv('tc_applied_rule.csv', index=False)

df_rules = pd.read_csv('/tmp/seedsim/siminfo/siminfo.csv', sep= ' ')
df_rules = df_rules[['Iter', 'tx_node_id', 'rx_node_id', 'LossRate']]

df_applied_rules = pd.read_csv('tc_applied_rule.csv', sep=',')

# Check the data types of columns
column_types = df_applied_rules.dtypes
print(column_types)
# Check if DataFrames are equal
are_equal = df_rules.equals(df_applied_rules)

print(are_equal)