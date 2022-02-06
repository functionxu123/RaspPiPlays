#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/02/05 15:27:33
@Author      :xuhao
'''
from ast import Store, parse
import os,sys
sys.path.append("..")
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
from common.common import MythreadBase, BUFFER_SIZE,SLEEPSHORT, SLEEPLONG

# 含微秒的日期时间 2018-09-06_21:54:46.205213
dt_ms = lambda: datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')

parser = argparse.ArgumentParser(description='server port map options')
parser.add_argument('-c',
                    "--configfile",
                    type=str,
                    default="./config.json",
                    help='a path for prot map config file, in json formate')
parser.add_argument("-d","--debug", action="store_true", default=False, help="open debug mode")

args = parser.parse_args()



# port info
with open(args.configfile, 'r') as f:
    PMAPS = json.load(f)

PORT2PORT = {int(x): int(PMAPS[x]) for x in PMAPS}

# init sockets
PORT2SOCK = {}
HOST = ''  #socket.INADDR_ANY

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
        self.log ("Listening on port: ", [x for x in  self.port2socket])
        try:
            while (not self.stop_thread):
                events = self.select_sock.select(None)
                for key, mask in events:
                    oriport = key.data
                    con, address = key.fileobj.accept()  # 在这个位置进行等待，监听端口号
                    con.setblocking(False)
                    self.log(" PID: ", os.getpid(), " Port: ", oriport," GetNewConnetctionFrom: ", address)

                    threadLock_PORT2CON.acquire()
                    if oriport not in PORT2CONS:
                        PORT2CONS[oriport]=[]
                    PORT2CONS[oriport].append(con)
                    threadLock_PORT2CON.release()                
        finally:
            self.log ("AcceptThread closing...")
            self.select_sock.close()
            for i in PORT2CONS:
                for j in PORT2CONS[i]:
                    j.close()

            for port in self.port2socket:
                self.port2socket[port].close()

            self.log ("AcceptThread: ", self.getName(), " Stoped")



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
        if self.listen_port not in PORT2CONS: return
        threadLock_PORT2CON.acquire()
        for sock in PORT2CONS[self.listen_port]:
            self.select_sock.register(sock, selectors.EVENT_READ, self.listen_port)
        threadLock_PORT2CON.release()
    
    def closesock(self, conn):
        self.log('One Closing Socket On ', self.listen_port)
        self.select_sock.unregister(conn)       

        threadLock_PORT2CON.acquire()
        PORT2CONS[self.listen_port].remove(conn)
        threadLock_PORT2CON.release() 

        conn.close()

    # fun to handle fd send/recv
    def run(self):
        try:
            self.log (" Starting SendThread: ",self.listen_port, " --> ", self.send_port)
            while not self.stop_thread:
                # client not connected
                if self.listen_port not in PORT2CONS or self.send_port not in PORT2CONS: 
                    sleep(SLEEPLONG)
                    if args.debug: self.log ("No connected sockets on ",self.send_port, " or ", self.listen_port)
                    continue

                threadLock_PORT2CON.acquire()
                tep_listen_socks= PORT2CONS[self.listen_port][:]   # copy.deepcopy(PORT2CONS[self.listen_port])
                tep_send_socks= PORT2CONS[self.send_port][:]   # copy.deepcopy(PORT2CONS[self.send_port])
                threadLock_PORT2CON.release()

                if len(tep_listen_socks)<=0 or len(tep_send_socks)<=0: 
                    sleep(SLEEPLONG)
                    if args.debug: self.log ("No connected sockets on ",self.send_port, " or ", self.listen_port)
                    continue

                # register all income sockets
                for soc in tep_listen_socks:
                    try:
                        self.select_sock.register(soc, selectors.EVENT_READ, self.listen_port)
                    except:
                        continue
                    finally:
                        pass

                events = self.select_sock.select(SLEEPSHORT)
                for key, mask in events:
                    oriport = key.data
                    conn=key.fileobj
                    data=None
                    try:
                        data = conn.recv(BUFFER_SIZE)
                    except:
                        data=None

                    if args.debug: self.log ("Recv from ", self.listen_port, " Got: ", len(data) if data else data)
                    if not data:
                        self.closesock(conn)
                        continue
                    
                    for sp in PORT2CONS[self.send_port]:
                        try:
                            sret=sp.sendall(data)
                            if sret is None:
                                if args.debug: self.log ("Send to port socket ", self.send_port, " Success")
                            else:
                                self.log ("Send to port socket ", self.send_port, " Failed : ", sret)
                        except:
                            continue
        finally:
            self.log ("SendThread %s closing..."%self.getName())
            self.select_sock.close()

            self.log ("SendThread %s Stoped..."%self.getName())
            
            



if __name__=="__main__":
    initsock()
    accept_threads=AcceptThread(PORT2SOCK)
    print ("Starting Accept thread...")
    accept_threads.start()

    send_threads=[]
    print ("Starting %d Send thread..."%(len(PORT2PORT)))
    for lisp in PORT2PORT:
        sendp=PORT2PORT[lisp]
        tep=SendThread(lisp, sendp)
        tep.start()
        send_threads.append(tep)
    
    print ("Serving...")
    try:
        while 1: sleep(15)
    except:
        pass
    finally:
        # close
        for i in send_threads: i.stop()
        for i in send_threads: i.join()

        accept_threads.stop()
        accept_threads.join()
    
    
