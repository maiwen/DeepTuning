# -*- coding: utf-8 -*-
"""
Created on 2018/5/21 14:30

@author: vincent
"""
import os
import time
import numpy as np
import zmq
import logging
import sys
import json
from .Env import *
import glob
import re
import datetime

_OSC_NUMS = 22
_OSC_PI_NUMS = 9
_LLITE_NUMS = 1
_LLITE_PI_NUMS = 9
_PARAMS = [{'name':'max_dirty_mb', 'initial': 32, 'min': 1, 'max': 4096, 'gap': 32, 'now': 32},
           {'name':'max_pages_per_rpc', 'initial': 256,'min': 1, 'max': 1024, 'gap': 64, 'now': 256},
           {'name':'max_rpcs_in_flight', 'initial': 8, 'min': 1, 'max': 256, 'gap': 4, 'now': 8},
           {'name':'max_read_ahead_mb', 'initial': 40, 'min': 0, 'max': 160, 'gap': 40, 'now': 40},
           {'name':'max_cached_mb', 'initial': 128, 'min': 128, 'max': 32234, 'gap': 128, 'now': 128},
           {'name':'max_read_ahead_per_file_mb', 'initial': 40, 'min': 0, 'max': 80, 'gap': 10, 'now': 40},
           {'name':'max_read_ahead_whole_mb', 'initial': 2, 'min': 0, 'max': 8, 'gap': 2, 'now': 2}]

_OSC_PI = ['cur_dirty_bytes', 'cur_grant_bytes', 'cur_lost_grant_bytes', 'destroys_in_flight']
stats = {}
old_stats = {}

class Lustre(Env):
    def __init__(self, node):
        Env.__init__(self)
        # os.popen('llstat -c /proc/fs/lustre/llite/sharefs*/stats')
        self.start = time.time()
        self.name = 'lustre_' + node
        self.state_dim = _OSC_NUMS * _OSC_PI_NUMS + _LLITE_NUMS * _LLITE_PI_NUMS
        self.action_dim = len(_PARAMS) * 2 + 1
        self.max_steps = None
        self.stats = {}
        self.old_stats = {}
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)

    def _getstates(self, window):
        # command = 'collectl -scdn -c1 -i3'
        # info = os.popen(command).read().split('\n')[3].split()
        # info = [float(i) for i in info]
        global stats
        global old_stats
        time.sleep(window)
        pis = []
        osc_paths = glob.glob('/proc/fs/lustre/osc/sharefs*/')
        osc_paths.sort()
        for osc_path in osc_paths:
            pis.extend(self._get_osc_pi(osc_path))
        llite_paths = glob.glob('/proc/fs/lustre/llite/sharefs*/')
        llite_paths.sort()
        for llite_path in llite_paths:
            pis.extend(self._get_llite_pi(llite_path))
        assert self.state_dim == len(pis)
        return pis

    def _get_osc_pi(self, osc_path):
        result = []
        for pi in _OSC_PI:
            result.append(self.read_proc_file(os.path.join(osc_path, pi)))

        with open(os.path.join(osc_path, 'import'), 'r') as importfile:
            # import is a proc file and should be read as a whole, i.e., not using readline()
            import_data = importfile.read()
            result.append(float(re.search('(?<=inflight: )[0-9.]+', import_data).group(0)))
            result.append(float(re.search('(?<=timeouts: )[0-9.]+', import_data).group(0)))
            result.append(float(re.search('(?<=avg_waittime: )[0-9.]+', import_data).group(0)))

        with open(os.path.join(osc_path, 'stats'), 'r') as statsfile:
            # import is a proc file and should be read as a whole, i.e., not using readline()
            stats_data = statsfile.read().split()
            if 'req_waittime' in stats_data:
                req_waittime = stats_data[stats_data.index('req_waittime') + 1]
            else:
                req_waittime = 0

            if 'req_active' in stats_data:
                req_active = stats_data[stats_data.index('req_active') + 1]
            else:
                req_active = 0
            result.append(float(req_waittime))
            result.append(float(req_active))
        return result

    def _get_llite_pi(self, llite_path):
        global stats
        global old_stats
        result = []
        with open(os.path.join(llite_path, 'stats'), 'r') as statsfile:
            # import is a proc file and should be read as a whole, i.e., not using readline()
            stats_data = statsfile.read().split()
            stats['snapshot_time'] = float(stats_data[1])
            if 'dirty_pages_hits' in stats_data:
                stats['dirty_pages_hits'] = float(stats_data[stats_data.index('dirty_pages_hits') + 1])
            else:
                stats['dirty_pages_hits'] = 0

            if 'dirty_pages_misses' in stats_data:
                stats['dirty_pages_misses'] = float(stats_data[stats_data.index('dirty_pages_misses') + 1])
            else:
                stats['dirty_pages_misses'] = 0

            if 'read_bytes' in stats_data:
                stats['read_operations'] = float(stats_data[stats_data.index('read_bytes') + 1])
                stats['read_bytes'] = float(stats_data[stats_data.index('read_bytes') + 6])
            else:
                stats['read_operations'], stats['read_bytes'] = 0, 0

            if 'write_bytes' in stats_data:
                stats['write_operations'] = float(stats_data[stats_data.index('write_bytes') + 1])
                stats['write_bytes'] = float(stats_data[stats_data.index('write_bytes') + 6])
            else:
                stats['write_operations'], stats['write_bytes'] = 0, 0

            if len(old_stats) <= 1:
                # read_throuput = stats['read_bytes'] / (stats['snapshot_time'] - self.start) / 1024 / 1024
                # write_throuput = stats['write_bytes'] / (stats['snapshot_time'] - self.start) / 1024 / 1024
                read_throuput = 0
                write_throuput = 0
                read_ops = 0
                write_ops = 0
                dirty_pages_hits = 0
                dirty_pages_misses = 0
                stats['reward'] = 0
            else:
                read_throuput = (stats['read_bytes'] - old_stats['read_bytes'] ) / (stats['snapshot_time'] - old_stats['snapshot_time']) / 1024 / 1024
                write_throuput = (stats['write_bytes'] - old_stats['write_bytes'] ) / (stats['snapshot_time'] - old_stats['snapshot_time']) / 1024 / 1024
                read_ops = (stats['read_operations'] - old_stats['read_operations'] ) / (stats['snapshot_time'] - old_stats['snapshot_time'])
                write_ops = (stats['write_operations'] - old_stats['write_operations'] ) / (stats['snapshot_time'] - old_stats['snapshot_time'])
                dirty_pages_hits = stats['dirty_pages_hits'] - old_stats['dirty_pages_hits']
                dirty_pages_misses = stats['dirty_pages_misses'] - old_stats['dirty_pages_misses']
                stats['reward'] = (read_throuput - old_stats['read_throuput']) + (write_throuput - old_stats['write_throuput']) + \
                                      (read_ops - old_stats['read_ops']) + ( write_ops - old_stats['write_ops'])

            old_stats['read_bytes'] = stats['read_bytes']
            old_stats['snapshot_time'] = stats['snapshot_time']
            old_stats['write_bytes'] = stats['write_bytes']
            old_stats['read_operations'] = stats['read_operations']
            old_stats['write_operations'] = stats['write_operations']
            old_stats['dirty_pages_hits'] = stats['dirty_pages_hits']
            old_stats['dirty_pages_misses'] = stats['dirty_pages_misses']
            old_stats['read_throuput'] = read_throuput
            old_stats['write_throuput'] = write_throuput
            old_stats['read_ops'] = read_ops
            old_stats['write_ops'] = write_ops

            result.append(float(read_throuput))
            result.append(float(write_throuput))
            result.append(float(read_ops))
            result.append(float(write_ops))
            result.append(float(dirty_pages_hits))
            result.append(float(dirty_pages_misses))
        with open(os.path.join(llite_path, 'max_cached_mb'), 'r') as cachedfile:
            cached_data = cachedfile.read()
            result.append(float(re.search('(?<=used_mb: )[0-9]+', cached_data).group(0)))
            result.append(float(re.search('(?<=unused_mb: )[0-9]+', cached_data).group(0)))
            result.append(float(re.search('(?<=reclaim_count: )[0-9]+', cached_data).group(0)))

        return result


    def read_proc_file(self, path):
        with open(path, 'rt') as procfile:
            try:
                return float(procfile.read(100))
            except (OSError, ValueError) as e:
                print('{type}: {msg}'.format(type=type(e).__name__, msg=str(e)))
                return 0

    def _execute_action(self, action):
        # lctl set_param -n /proc/fs/lustre/osc/scrachfs*/max_rpcs_in_flight=16
        set_osc = 'lctl set_param -n /proc/fs/lustre/osc/sharefs*/'
        set_llite = 'lctl set_param -n /proc/fs/lustre/llite/sharefs*/'
        if action != 0:
            index = (action - 1) // 2    # action map to _PARAMS index
            now_value = _PARAMS[index]['now']
            if action % 2 == 0:
                if int(now_value) + _PARAMS[index]['gap'] > _PARAMS[index]['max']:
                    pass
                else:
                    if index < 3 :
                        os.popen(set_osc + _PARAMS[index]['name'] + '=' + str(int(now_value) + _PARAMS[index]['gap']))
                        _PARAMS[index]['now'] = int(now_value) + _PARAMS[index]['gap']
                    else:
                        os.popen(set_llite + _PARAMS[index]['name'] + '=' + str(int(now_value) + _PARAMS[index]['gap']))
                        _PARAMS[index]['now'] = int(now_value) + _PARAMS[index]['gap']
            else:
                if int(now_value) - _PARAMS[index]['gap'] < _PARAMS[index]['min']:
                    pass
                else:
                    if index < 3 :
                        os.popen(set_osc + _PARAMS[index]['name'] + '=' + str(int(now_value) - _PARAMS[index]['gap']))
                        _PARAMS[index]['now'] = int(now_value) - _PARAMS[index]['gap']
                    else:
                        os.popen(set_llite + _PARAMS[index]['name'] + '=' + str(int(now_value) - _PARAMS[index]['gap']))
                        _PARAMS[index]['now'] = int(now_value) - _PARAMS[index]['gap']

    def reset(self):
        #  monitor metrics
        set_osc = 'lctl set_param -n /proc/fs/lustre/osc/sharefs*/'
        set_llite = 'lctl set_param -n /proc/fs/lustre/llite/sharefs*/'
        for param in _PARAMS[:3]:
            os.popen(set_osc + param['name'] + '=' + str(param['initial']))
        for param in _PARAMS[3:7]:
            os.popen(set_llite + param['name'] + '=' + str(param['initial']))
        return self._getstates()

    def step(self):
        self.reset()
        paras = {}
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect("tcp://tensorflow.ihep.ac.cn:5555")
        handler = logging.FileHandler(self.name+'.log')
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('[ %(asctime)s - %(name)s ]  - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        while True:
            states = self._getstates(10)
            #  Recording the adjustment process for human reference
            with open('log/' + self.name + '_tuning.log', 'a') as f:
                for p in _PARAMS:
                    paras[p['name']] = p['now']
                tuning = dict(time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), paras=paras,
                              rt=old_stats['read_throuput'], wt=old_stats['write_throuput'])
                f.write(json.dumps(tuning) + '\n')

            reward = stats['reward']
            message = json.dumps(dict(name=self.name, states=states, reward=reward))
            socket.send_string(message)
            self.logger.info('send ' + message + ' to  tensorflow.ihep.ac.cn:5555')
            action = socket.recv()
            self.logger.info('receive action: ' + action)
            if int(action) == -1 :
                break
            self._execute_action(int(action))



