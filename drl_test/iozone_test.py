# -*- coding: utf-8 -*-
"""
Created on 2018/6/7 20:24

@author: vincent
"""

import os
import time
import datetime

def complex(i):
    info = os.popen('iozone -i 0 -i 1 -i 2 -i 5 –r 1M–j 2M -s 8G -t 32 -+m /afs/ihep.ac.cn/users/z/zhangwt/nodelist -o -w -C |tee –a /afs/ihep.ac.cn/users/z/zhangwt/a2c_iozone'+str(i)+'.log').read()

count = 4
start = time.time()
print('iozone start at: ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

while (time.time() - start) < 24 * 60 * 60 :
    complex(count)
    count += 1

print('iozone end at: ' + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))