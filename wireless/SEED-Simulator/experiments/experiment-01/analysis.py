#!/bin/env python3 

import pandas as pd
import matplotlib.pyplot as plt

def performance_plot(csv_path):
    # Read the CSV file into a DataFrame
    df = pd.read_csv(csv_path, delimiter=" ")
    iterations = [1, 5, 10]
    colors = ['blue', 'orange', 'green']
    markers = ['o', 's', 'x']
    x_list = []
    y_list = []
    
    for i, iter in enumerate(iterations):
        data = df[df["Iterations"]==iter]
    
        plt.subplot(2, 2, i+1)  # First plot
        # Plot the data
        x = data['NumNodes'].copy()
        y = data['ElaspedTime'].copy()
        x_list.append(x)
        y_list.append(y)
        plt.plot(x, y, color=colors[i], marker=markers[i])
        plt.title('{} iteration(s)'.format(iter))
        
        # Adding labels and a legend
        plt.xlabel('Num Nodes')
        plt.ylabel('Elapsed Time (sec)')
    
    plt.subplot(2, 2, 4)  # Fourth plot
    # plt.plot(x, y4)
    plt.title('Total')
    
    for i, iter in enumerate(iterations):
        plt.plot(x_list[i], y_list[i], label='iter {}'.format(iter), marker=markers[i])
    
    # Adding labels and a legend
    plt.xlabel('Num Nodes')
    plt.ylabel('Elapsed Time (sec)')
    plt.legend()
        
    # Add a main title to the entire figure
    plt.suptitle(csv_path.split(".")[0])
    
    # Adjust layout to prevent clipping of titles
    plt.tight_layout()
    
    # Display the plot
    # plt.show()
    # Save the plot
    plt.savefig('figs/'+csv_path.split('.')[0])



performance_plot("v2v-urban-seed-test.csv")
performance_plot("v2v-highway-seed-test.csv")

