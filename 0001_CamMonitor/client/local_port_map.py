#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/02/06 00:11:17
@Author      :xuhao
'''
from fnmatch import fnmatch
import os, sys

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
from common.common import BUFFER_SIZE, MythreadBase

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
with open(args.configfile, 'r') as f:
    IPPORT2IPPORT = json.load(f)

parsefun = lambda x: (x.split(":")[0].strip(), int(x.split(":")[1].strip()))
TUIPPORT2TUIPPORT = {
    parsefun(x): parsefun(IPPORT2IPPORT[x])
    for x in IPPORT2IPPORT
}

threadLock_TUIPPORT2SOCK= threading.Lock()
TUIPPORT2SOCK = {}


def initsock():
    # socket.setdefaulttimeout(2)
    for i in TUIPPORT2TUIPPORT:
        TUIPPORT2SOCK[i] = None
        TUIPPORT2SOCK[TUIPPORT2TUIPPORT[i]] = None

    for ipport in TUIPPORT2SOCK:
        # 创建一个TCP套接字
        ser = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM
        )  # 套接字类型AF_INET, socket.SOCK_STREAM   tcp协议，基于流式的协议
        # 对socket的配置重用ip和端口号
        ser.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # ser.connect(ipport)
        #ser.setblocking(False)

        TUIPPORT2SOCK[ipport] = ser
        #print (ser.connect_ex(ipport))


# thread handle fd
class SendThread(MythreadBase):

    def __init__(self, listen_ipport, send_ipport):
        MythreadBase.__init__(self)
        self.stop_thread = False
        self.connected = False

        self.listen_ipport = listen_ipport
        self.send_ipport = send_ipport
        self.listen_sock = TUIPPORT2SOCK[listen_ipport]
        self.send_sock = TUIPPORT2SOCK[send_ipport]

    def tryconnect(self, sock, ipport):
        if self.connected: return True
        ret = sock.connect_ex(ipport)
        # ErrorCode:  106 : Transport endpoint is already connected
        if ret != 0 and ret!=106:
            print("Trying Connecting to ", ipport, " ErrorCode: ", ret, ":", os.strerror(ret))
            return False
        return True

    def closesock(self, sock):
        if sock == self.listen_sock:
            print('One Closing Socket On ', self.listen_ipport)
            sock.close()
            
            self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            threadLock_TUIPPORT2SOCK.acquire()
            TUIPPORT2SOCK[self.listen_ipport]=self.listen_sock
            threadLock_TUIPPORT2SOCK.release()
        else:
            print('One Closing Socket On ', self.send_ipport)
            sock.close()
            
            self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            threadLock_TUIPPORT2SOCK.acquire()
            TUIPPORT2SOCK[self.send_ipport]=self.send_sock
            threadLock_TUIPPORT2SOCK.release()

    def run(self):
        try:
            print ("Thread: ", self.getName(),"Staring Connection Thread: ", self.listen_ipport, " --> ", self.send_ipport)
            while not self.stop_thread:
                if (not self.tryconnect(self.listen_sock, self.listen_ipport)) or (
                        not self.tryconnect(self.send_sock, self.send_ipport)):
                    sleep(5)
                    continue
                self.connected = True

                print ("Connection Success")

                while (not self.stop_thread) and self.connected:
                    data = None
                    try:
                        data = self.listen_sock.recv(BUFFER_SIZE)
                    except:
                        data = None

                    #print("Recv from ", self.listen_ipport, " Got: ",
                        len(data) if data else data)
                    if not data:
                        self.connected = False
                        self.closesock(self.listen_sock)
                        break

                    try:
                        sret=self.send_sock.sendall(data)
                        if sret is None:
                            pass #print ("Send to port socket ", self.send_ipport, " Success")
                        else:
                            print ("Send to port socket ", self.send_ipport, " Failed : ", sret)
                    except:
                        sleep(1)
                        continue
        finally:
            print ("SendThread %s closing..."%self.getName())
            self.listen_sock.close()
            self.send_sock.close()
            print ("SendThread %s Stoped..."%self.getName())
                    



if __name__ == "__main__":
    initsock()

    send_threads=[]
    for i in TUIPPORT2TUIPPORT:
        target_ipport=TUIPPORT2TUIPPORT[i]
        tep= SendThread(i, target_ipport)
        tep.start()
        send_threads.append(tep)

    try:
        while 1: sleep(15)
    except:
        pass
    finally:
        for i in send_threads: i.stop()
        for i in send_threads: i.join()