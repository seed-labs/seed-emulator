#!/bin/env python3 

import pandas as pd
import matplotlib.pyplot as plt
#############################################
# 1. plot txpower_result.csv 
csv_path = 'frequency_result.csv'
df = pd.read_csv(csv_path, delimiter=" ")
x = df['Frequency'].copy()/1.0e9
y = df['LossRate'].copy()

plt.plot(x, y)
plt.title('[ Frequency (GHz) - LossRate (%) ]')
plt.xlabel('Frequency (GHz)')
plt.ylabel('LossRate (%)')

plt.savefig('figs/exp3-fig1.png')
plt.clf()

#############################################
# 2. plot frequency_result.csv 
csv_path = 'txpower_result.csv'
df = pd.read_csv(csv_path, delimiter=" ")
x = df['TxPower'].copy()
y = df['LossRate'].copy()

plt.plot(x, y)
plt.title('[ TxPower (dBm) - LossRate (%) ]')
plt.xlabel('TxPower (dBm)')
plt.ylabel('LossRate (%)')

plt.savefig('figs/exp3-fig2.png')
plt.clf()

#############################################
# 3. plot frequency_result.csv 
csv_path = 'distance_result.csv'
df = pd.read_csv(csv_path, delimiter=" ")
x = df['Distance'].copy()
y = df['LossRate'].copy()

plt.plot(x, y)
plt.title('[ Distance (m) - LossRate (%) ]')
plt.xlabel('Distance (m)')
plt.ylabel('LossRate (%)')

plt.savefig('figs/exp3-fig3.png')
plt.clf()
