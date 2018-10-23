# -*- coding: utf-8 -*-
"""
Created on Tue Jul  3 10:33:13 2018

@author: vincent
"""

import numpy as np

algorithms = ['base','dqn','a2c','ppo']

base, dqn, a2c, ppo = np.zeros([7,4]), np.zeros([7,4]), np.zeros([7,4]), np.zeros([7,4])

for alg in algorithms:
    for i in range(4):
        with open(alg+'_iozone'+str(i)+'.log','r') as f:
            info = f.readlines()
            count = 0
            for line in info:
                if 'Avg throughput per process' in line:
                    globals()[alg][count][i] = line.split()[5]
                    count += 1
    print(globals()[alg])
    