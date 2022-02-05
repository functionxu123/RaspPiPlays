#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/02/05 15:27:33
@Author      :xuhao
'''
from email.charset import add_codec
import os
import os.path as op
import argparse
import json
from datetime import datetime
import threading
import socket
import multiprocessing
from multiprocessing import Array
import ctypes 
import selectors

# 含微秒的日期时间 2018-09-06_21:54:46.205213
dt_ms = lambda: datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')

parser = argparse.ArgumentParser(description='server port map options')
parser.add_argument('-c',
                    "--configfile",
                    type=str,
                    default="./config.json",
                    help='a path for prot map config file, in json formate')

args = parser.parse_args()



# port info
PMAPS = json.load(args.configfile)

PORT2PORT = {int(x): int(PMAPS[x]) for x in PMAPS}

# init sockets
PORT2SOCK = {}
HOST = ''  #socket.INADDR_ANY
BUFFER_SIZE = 1024

def initsock():
    # socket.setdefaulttimeout(2)
    for i in PORT2PORT:
        PORT2SOCK[i] = None
        PORT2SOCK[PORT2PORT[i]] = None

    for port in PORT2SOCK:
        # 创建一个TCP套接字
        ser = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM)  # 套接字类型AF_INET, socket.SOCK_STREAM   tcp协议，基于流式的协议
        # 对socket的配置重用ip和端口号
        ser.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        # 绑定端口号
        ser.bind((HOST, port))  #  写哪个ip就要运行在哪台机器上
        # 设置半连接池
        ser.listen(5)  # 最多可以连接多少个客户端
        ser.setblocking(False)
        PORT2SOCK[port] = ser
        

#init done

# accept thread
threadLock_PORT2CON = threading.Lock()
PORT2CONS = {}

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
    
    def stop(self):
        self.stop_thread = True
        print("Stoping Thread: ", self.getName(), " PID: ", os.getpid())

        thread_id = self.get_id() 
        #给线程发过去一个exceptions响应
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit)) 
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1: 
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, None) 
            print('Exception raise failure')

class AcceptThread(MythreadBase):

    def __init__(self, port2socket):
        MythreadBase.__init__(self)
        self.stop_thread = False
        self.port2socket=port2socket
        self.select_sock=selectors.DefaultSelector()
        for port in self.port2socket:
            self.select_sock.register(self.port2socket[port], selectors.EVENT_READ, port)


    # function to handle accept
    def run(self):
        try:
            while (not self.stop_thread):
                events = self.select_sock.select(None)
                for key, mask in events:
                    oriport = key.data
                    con, address = key.fileobj.accept()  # 在这个位置进行等待，监听端口号
                    con.setblocking(False)
                    print("Thread: ", self.getName(), " PID: ", os.getpid(), " Port: ", oriport," GetNewConnetctionFrom: ", address)

                    threadLock_PORT2CON.acquire()
                    if oriport not in PORT2CONS:
                        PORT2CONS[oriport]=[]
                    PORT2CONS[oriport].append(con)
                    threadLock_PORT2CON.release()                
        finally:
            self.select_sock.close()
            for i in PORT2CONS:
                for j in PORT2CONS[i]:
                    j.close()

            for port in self.port2socket:
                self.port2socket[port].close()

            print ("Thread: ", self.getName(), " Stoped")



# process handle port
class PortMapProcess(multiprocessing.Process):

    def __init__(self, listen_port=80, send_port=9090):
        multiprocessing.Process.__init__(self)
        self.listen_port = listen_port
        self.send_port = send_port
        self.listen_socket = PORT2SOCK[
            self.listen_port] if self.listen_port in PORT2SOCK else None
        self.send_socket = PORT2SOCK[
            self.send_port] if self.send_port in PORT2SOCK else None
        self.stop_process = False
        self.con_listen = []
        self.con_send = []
        self.threads_listen = []

    #fun to handle port accept
    def run(self):
        while not self.stop_process:
            con, address = self.listen_socket.accept()  # 在这个位置进行等待，监听端口号
            print("Process: ", self.name, " PID: ", os.getpid(),
                  " GetNewConnetction: ", address)
            tep = SendThread()

    def stop(self):
        for i in self.threads_listen:
            i.stop()
            i.join()
        self.stop_process = True
        print("Stoping Process: ", self.name, " PID: ", os.getpid())
        self.kill()


# thread handle fd
class SendThread(MythreadBase):

    def __init__(self, listen_port, send_port):
        MythreadBase.__init__(self)
        self.stop_thread = False
        self.listen_port=listen_port
        self.send_port=send_port
        self.select_sock=selectors.DefaultSelector()
        self.initsel()
    
    def initsel(self):
        threadLock_PORT2CON.acquire()
        for sock in PORT2CONS[self.listen_port]:
            self.select_sock.register(sock, selectors.EVENT_READ, self.listen_port)
        threadLock_PORT2CON.release()
    
    def closesock(self, conn):
        print('One Closing Socket On ', self.listen_port)
        self.select_sock.unregister(conn)       

        threadLock_PORT2CON.acquire()
        PORT2CONS[self.listen_port].remove(conn)
        threadLock_PORT2CON.release() 

        conn.close()

    # fun to handle fd send/recv
    def run(self):
        while not self.stop_thread:
            # client not connected
            if self.listen_port not in PORT2CONS: continue
            if self.send_port not in PORT2CONS: continue

            events = self.select_sock.select(0)
            for key, mask in events:
                oriport = key.data
                conn=key.fileobj
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    self.closesock(conn)
            
            



if __name__=="__main__":
    initsock()
    accept_threads=AcceptThread(PORT2SOCK)
    accept_threads.start()

    
    

    # close
    accept_threads.stop()
    accept_threads.join()
    
    
