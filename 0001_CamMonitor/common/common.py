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


# 含微秒的日期时间 2018-09-06_21:54:46.205213
dt_ms = lambda: datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')

BUFFER_SIZE = 1024*2

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
        print("Stoping Thread: ", self.getName(), " PID: ", os.getpid())

        thread_id = self.get_id() 
        #给线程发过去一个exceptions响应
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit)) 
        self.stop_thread = True
        if res == 0:
            #raise ValueError("invalid thread id")
            print ("Invalid thread id: ", thread_id)
        elif res != 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None) 
            print('Exception raise failure')