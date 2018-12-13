# -*- coding: utf-8 -*-
"""
Created on 2018/5/22 20:16

@author: vincent
"""
from common import Lustre
import socket

lustre = Lustre(socket.gethostname())
lustre.reset()