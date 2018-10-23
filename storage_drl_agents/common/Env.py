# -*- coding: utf-8 -*-
"""
Created on 2018/5/21 11:10

@author: vincent
"""
import numpy as np

class Env(object):
    def __init__(self):
        self.name = None
        self.state_dim = None
        self.action_dim = None
        self.max_steps = None

    def reset(self):
        pass

    def step(self, action):
        pass

    def seed(self, random_seed):
        pass

