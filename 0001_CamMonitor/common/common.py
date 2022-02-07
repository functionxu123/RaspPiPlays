#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/02/06 01:10:20
@Author      :xuhao
'''
import threading
import socket
import os
import os.path as op
import ctypes, copy
import selectors
import inspect
from datetime import datetime


# 含微秒的日期时间 2018-09-06_21:54:46.205213
dt_ms = lambda: datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')

BUFFER_SIZE = int(1024)

MAXSENDTRY=6

SLEEPLONG=6
SLEEPSHORT=1

class MythreadBase(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.stop_thread = False
    
    def run(self):
        pass

    def get_id(self): 
		# returns id of the respective thread 
        if hasattr(self, '_thread_id'): 
            return self._thread_id 
        for id, thread in threading._active.items(): 
            if thread is self: return id
        return -1
    
    def stop(self):
        self.log("Stoping Thread: ", self.getName(), " PID: ", os.getpid())

        thread_id = ctypes.c_long(self.ident) #self.get_id() 
        exctype=SystemExit
        if not inspect.isclass(exctype):    exctype = type(exctype)

        #给线程发过去一个exceptions响应
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(exctype)) 
        self.stop_thread = True
        if res == 0:
            raise ValueError("invalid thread id")
            #self.log ("Invalid thread id: ", thread_id)
        elif res != 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None) 
            self.log('Exception raise failure')
        else:
            self.log ("Send SystemExit to %s Success"%self.getName())
    
    def log(self, *args):
        print ("[",self.getName(), "] ", *args)