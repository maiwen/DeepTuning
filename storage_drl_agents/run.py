# -*- coding: utf-8 -*-
"""
Created on 2018/5/23 20:11

@author: vincent
"""


from agents.A2C import A2C
from agents.ACKTR import JointACKTR as ACKTR
from agents.DQN import DQN
from agents.PPO import PPO
from common.utils import agg_double_list
from common import *
import argparse
import sys
import os
import gym
import numpy as np
import matplotlib.pyplot as plt
import zmq
import json
import logging


MAX_EPISODES = 5000
MAX_STEPS = 200000
EPISODES_BEFORE_TRAIN = 0
STEPS_BEFORE_TRAIN = 1000
EVAL_EPISODES = 10
EVAL_INTERVAL = 100

# roll out n steps
ROLL_OUT_N_STEPS = 10
MEMORY_CAPACITY = 20000
BATCH_SIZE = 200

REWARD_DISCOUNTED_GAMMA = 0.99
ENTROPY_REG = 0.00
DONE_PENALTY = -10.

CRITIC_LOSS = "mse"
MAX_GRAD_NORM = None

EPSILON_START = 0.99
EPSILON_END = 0.05
EPSILON_DECAY = 500

TARGET_UPDATE_STEPS = 5
TARGET_TAU = 1.0
RANDOM_SEED = 2017


def run(name = 'dqn'):

    env = Lustre('logger')
    state_dim = env.state_dim
    action_dim = env.action_dim

    agents = {'dqn': DQN(env=env, memory_capacity=MEMORY_CAPACITY,
                state_dim=state_dim, action_dim=action_dim,
                batch_size=BATCH_SIZE, max_steps=MAX_STEPS,
                done_penalty=DONE_PENALTY, critic_loss=CRITIC_LOSS,
                reward_gamma=REWARD_DISCOUNTED_GAMMA,
                epsilon_start=EPSILON_START, epsilon_end=EPSILON_END,
                epsilon_decay=EPSILON_DECAY, max_grad_norm=MAX_GRAD_NORM,
                episodes_before_train=EPISODES_BEFORE_TRAIN),

              'a2c': A2C(env=env, memory_capacity=MEMORY_CAPACITY,
                state_dim=state_dim, action_dim=action_dim,max_steps=MAX_STEPS,
                batch_size=BATCH_SIZE, entropy_reg=ENTROPY_REG,
                done_penalty=DONE_PENALTY, roll_out_n_steps=ROLL_OUT_N_STEPS,
                reward_gamma=REWARD_DISCOUNTED_GAMMA,
                epsilon_start=EPSILON_START, epsilon_end=EPSILON_END,
                epsilon_decay=EPSILON_DECAY, max_grad_norm=MAX_GRAD_NORM,
                episodes_before_train=EPISODES_BEFORE_TRAIN,
                critic_loss=CRITIC_LOSS),

              'acktr': ACKTR(env=env, memory_capacity=MEMORY_CAPACITY,
                  state_dim=state_dim, action_dim=action_dim,max_steps=MAX_STEPS,
                  batch_size=BATCH_SIZE, entropy_reg=ENTROPY_REG,
                  done_penalty=DONE_PENALTY, roll_out_n_steps=ROLL_OUT_N_STEPS,
                  reward_gamma=REWARD_DISCOUNTED_GAMMA,
                  epsilon_start=EPSILON_START, epsilon_end=EPSILON_END,
                  epsilon_decay=EPSILON_DECAY, max_grad_norm=MAX_GRAD_NORM,
                  episodes_before_train=EPISODES_BEFORE_TRAIN,
                  critic_loss=CRITIC_LOSS, use_cuda=False),

              'ppo': PPO(env=env, memory_capacity=MEMORY_CAPACITY,
                state_dim=state_dim, action_dim=action_dim,max_steps=MAX_STEPS,
                batch_size=BATCH_SIZE, entropy_reg=ENTROPY_REG,
                done_penalty=DONE_PENALTY, roll_out_n_steps=ROLL_OUT_N_STEPS,
                target_update_steps=TARGET_UPDATE_STEPS, target_tau=TARGET_TAU,
                reward_gamma=REWARD_DISCOUNTED_GAMMA,
                epsilon_start=EPSILON_START, epsilon_end=EPSILON_END,
                epsilon_decay=EPSILON_DECAY, max_grad_norm=MAX_GRAD_NORM,
                episodes_before_train=EPISODES_BEFORE_TRAIN,
                critic_loss=CRITIC_LOSS)}

    agent = agents[name]

    episodes =[]
    eval_rewards =[]
    clients = []
    old_state, old_action = {}, {}
    rewards = 0
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    if load:
        agent.load(name)
        print('load trained '+ name + ' model successfully')

    while agent.n_steps <= agent.max_steps:
        message = socket.recv()
        message = json.loads(message)
        if message['name'] not in clients:
            clients.append(message['name'])
            old_state[message['name']] = [0] * agent.state_dim
            old_action[message['name']] = 0

        logger.info(' received '+ str(message) + ' from ' + message['name'])

        agent.env_state = message['states']
        reward = message['reward']

        agent.n_steps += 1
        rewards += reward

        agent.memory._push_one(old_state[message['name']], old_action[message['name']], reward, agent.env_state, 0)

        action = agent.exploration_action(agent.env_state)
        socket.send_string(str(action))
        logger.info(' send ' + str(action) + ' to ' + message['name'])

        old_state[message['name']] = agent.env_state
        old_action[message['name']] = action
        with open('log/' + name + '_reward.log', 'a') as f:
            f.write(' steps: ' + str(agent.n_steps - 1) + ' , action: ' + str(old_action[message['name']])+ ' , reward: ' + str(reward) + '\n')
        if agent.n_steps > STEPS_BEFORE_TRAIN:
            agent.train()
        if agent.n_steps % 1000 == 0 and agent.n_steps > 0:
            with open( 'log/'+name+'_rewards.log', 'a') as f:
                f.write(' steps: ' + str(agent.n_steps) + ' , rewards: ' + str(rewards) + '\n')
        if agent.n_steps % 5000 == 0 and agent.n_steps > 0:
            agent.save(name)
        if agent.n_steps >= agent.max_steps:
            action = -1
            socket.send_string(str(action))

        # if a2c.episode_done and ((a2c.n_episodes+1)%EVAL_INTERVAL == 0):
        #     rewards, _ = a2c.evaluation(env, EVAL_EPISODES)
        #     rewards_mu, rewards_std = agg_double_list(rewards)
        #     print("Episode %d, Average Reward %.2f" % (a2c.n_episodes+1, rewards_mu))
        #     episodes.append(a2c.n_episodes+1)
        #     eval_rewards.append(rewards_mu)

    episodes = np.array(episodes)
    eval_rewards = np.array(eval_rewards)
    np.savetxt("./output/%s_a2c_episodes.txt"%env.name, episodes)
    np.savetxt("./output/%s_a2c_eval_rewards.txt"%env.name, eval_rewards)

    plt.figure()
    plt.plot(episodes, eval_rewards)
    plt.title("%s"%env.name)
    plt.xlabel("Episode")
    plt.ylabel("Average Reward")
    plt.legend(["A2C"])
    plt.savefig("./output/%s_a2c.png"%env.name)

def parse_args():
    """Parse the args."""
    parser = argparse.ArgumentParser(
        description='storage drl')
    parser.add_argument('--agent', type=str, required=False,
                        default='dqn',
                        help='choose agent from [dqn, a2c, ppo]')
    parser.add_argument('--load', type=bool, required=False,
                        default=1,
                        help='load trained model')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    logger = logging.getLogger(args.agent)
    load = args.load
    logger.setLevel(logging.INFO)

    # create a file handler
    handler = logging.FileHandler('log/'+args.agent + '.log')
    handler.setLevel(logging.INFO)

    # create a logging format
    formatter = logging.Formatter('[ %(asctime)s - %(name)s ]  - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)
    run(args.agent)
