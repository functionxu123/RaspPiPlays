#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@Date     :2022/01/26 22:49:34
@Author      :xuhao
'''

import cv2
from http import server

import time

video = cv2.VideoCapture(0)
if video is None:
    print ("Couldn't open camera...")
    exit(0)

def GetJpegFrame(vcap):
    suc, img=vcap.read()
    if not suc:
        print ("Get image error")
        return None
    ret, jpg = cv2.imencode('.jpg', img)
    print ("cam get img:", img.shape)
    return jpg.tobytes()

def gen(camera):
    while True:
        frame = GetJpegFrame(camera)
        # 使用generator函数输出视频流， 每次请求输出的content类型是image/jpeg
        yield (b'--frame\r\n'+  b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n') 

def GetFramePacket(vcap):
    frame=GetJpegFrame(vcap)
    return b'--frame\r\n'+b'Content-Type: image/jpeg\r\n\r\n '+frame+b'\r\n\r\n'

class HTTPHandler(server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/video":
            self.send_response(200)
            self.send_header('Content-Type','multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            while 1:
                #self.wfile.write(GetFramePacket(video) )
                self.wfile.write(next(cam) )
                self.wfile.write(b'\r\n')
                #time.sleep(1)
        else:
            self.send_error(404)
            self.end_headers()

print ("starting http server...")

cam=gen(video)
try:
    addr=('', 8080)
    ser=server.HTTPServer(addr, HTTPHandler)
    ser.serve_forever()
except:
    print ("Done serve")
finally:
    video.release()

