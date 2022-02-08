#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/02/06 00:11:17
@Author      :xuhao
'''
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
from common.common import BUFFER_SIZE, MythreadBase, MAXSENDTRY, SLEEPLONG, SLEEPSHORT

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
    '''
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
    '''


# thread handle fd
class SendThread(MythreadBase):

    def __init__(self, listen_ipport, send_ipport):
        MythreadBase.__init__(self)
        self.stop_thread = False
        self.connected_listen=False
        self.connected_send=False

        self.listen_ipport = listen_ipport
        self.send_ipport = send_ipport

    def tryconnect_listen(self):
        if TUIPPORT2SOCK[self.listen_ipport] is None:
            threadLock_TUIPPORT2SOCK.acquire()
            TUIPPORT2SOCK[self.listen_ipport]=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            threadLock_TUIPPORT2SOCK.release()
            self.connected_listen=False

        if self.connected_listen: return True
        ret = TUIPPORT2SOCK[self.listen_ipport].connect_ex(self.listen_ipport)
        # ErrorCode:  106 : Transport endpoint is already connected
        if ret != 0 and ret!=106:
            self.log("Trying Connecting to ", self.listen_ipport, " ErrorCode: ", ret, ":", os.strerror(ret))
            return False
        return True

    def refresh_sock(self, ipport):
        self.log('One Refreshing Socket On ', ipport)
        
        threadLock_TUIPPORT2SOCK.acquire()
        if ipport in TUIPPORT2SOCK and (TUIPPORT2SOCK[ipport] is not None): TUIPPORT2SOCK[ipport].close()
        TUIPPORT2SOCK[ipport]=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        threadLock_TUIPPORT2SOCK.release()
    
    def close_sock(self, ipport):
        self.log('One Closing Socket On ', ipport)

        threadLock_TUIPPORT2SOCK.acquire()
        if ipport in TUIPPORT2SOCK and (TUIPPORT2SOCK[ipport] is not None): TUIPPORT2SOCK[ipport].close()
        TUIPPORT2SOCK[ipport]=None
        threadLock_TUIPPORT2SOCK.release()
    
    def run(self):
        try:
            self.log ("Staring Connection Thread: ", self.listen_ipport, " --> ", self.send_ipport)
            while not self.stop_thread:
                #  or (not self.tryconnect(self.send_sock, self.send_ipport)
                while ((not self.connected_listen) and (not self.tryconnect_listen(self.listen_ipport))):
                    sleep(SLEEPLONG)
                    continue
                if not self.connected_listen: self.log ("Connection Listen Success: ", self.listen_ipport)
                self.connected_listen = True                

                # recv
                data = b''
                try:
                    if TUIPPORT2SOCK[self.listen_ipport] is None: 
                        self.connected_listen = False 
                        continue
                    if args.debug: self.log("Prepare Blocked Reciving From ",self.listen_ipport)
                    data = TUIPPORT2SOCK[self.listen_ipport].recv(BUFFER_SIZE)
                except:
                    data = None

                if args.debug:  self.log("Recv from ", self.listen_ipport, " Got: ", len(data) if data else data)

                if data is None:
                    self.close_sock(self.listen_ipport)
                    self.connected_listen = False
                    continue
                elif not data:
                    self.connected_listen = False
                    self.close_sock(self.listen_ipport)
                    self.connected_send= False
                    self.close_sock(self.send_ipport)
                    continue
                # send 
                send_cnt=0
                while send_cnt<MAXSENDTRY:
                    send_cnt+=1

                    # while ((not self.connected_send) and 
                    #     (not self.tryconnect(TUIPPORT2SOCK[self.send_ipport], self.send_ipport))):
                    #     sleep(SLEEPLONG)
                    #     continue
                    # if not self.connected_send: self.log ("Connection Send Success: ", self.send_ipport)
                    # self.connected_send=True

                    try:
                        if TUIPPORT2SOCK[self.send_ipport] is None: 
                            if args.debug: self.log("Send sock not ready: ",self.send_ipport," Waiting ...." )
                            sleep(SLEEPSHORT)
                            continue
                        
                        if args.debug: self.log("Prepare Blocked Sending to ",self.send_ipport)
                        sret=TUIPPORT2SOCK[self.send_ipport].sendall(data)
                        if sret is None:
                            if args.debug: self.log ("Send to port socket ", self.send_ipport, " Success")
                        else:
                            self.log ("Send to port socket ", self.send_ipport, " Failed : ", sret)
                            #self.closesock_ipport(self.send_ipport)
                            #self.connected_send=False
                            sleep(SLEEPSHORT)
                            continue
                    except Exception as e:
                        if args.debug: 
                            self.log ("send_sock.sendall Error: ",str(e))
                        #self.closesock_ipport(self.send_ipport)
                        #self.connected_send=False
                        sleep(SLEEPSHORT)
                        continue

                    break
                if send_cnt>=MAXSENDTRY:
                    if args.debug: self.log ("Max Send Cnt > ",MAXSENDTRY," Discarding some data...")
                    
        finally:
            self.log ("SendThread %s closing..."%self.getName())
            if self.send_ipport in TUIPPORT2SOCK and (TUIPPORT2SOCK[self.send_ipport] is not None): TUIPPORT2SOCK[self.send_ipport].close()
            if self.listen_ipport in TUIPPORT2SOCK and (TUIPPORT2SOCK[self.listen_ipport] is not None): TUIPPORT2SOCK[self.listen_ipport].close()
            self.log ("SendThread %s Stoped..."%self.getName())



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