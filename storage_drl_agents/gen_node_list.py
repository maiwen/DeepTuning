import os

nodes = [['lustretest1', '/sharefs/cctest/zhangwt/', '/afs/ihep.ac.cn/users/z/zhangwt/iozone3_479/src/current/iozone'],
        ['stortest01.ihep.ac.cn', '/sharefs/cctest/zhangwt/',
         '/afs/ihep.ac.cn/users/z/zhangwt/iozone3_479/src/current/iozone']]
with open('nodelist', 'a') as f:
    for node in nodes:
        for _ in range(16):
            f.write(node[0]+' '+node[1]+' '+node[2]+ '\n')