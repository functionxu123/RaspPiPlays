#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/02/06 00:11:17
@Author      :xuhao
'''
import os
import os.path as op
import argparse
import json
from datetime import datetime
import threading
import socket
import multiprocessing
from multiprocessing import Array
import ctypes, copy
import selectors
from time import sleep

# 含微秒的日期时间 2018-09-06_21:54:46.205213
dt_ms = lambda: datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')

parser = argparse.ArgumentParser(description='server port map options')
parser.add_argument('-c',
                    "--configfile",
                    type=str,
                    default="./config.json",
                    help='a path for prot map config file, in json formate')

args = parser.parse_args()