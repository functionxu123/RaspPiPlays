#!/usr/bin/env python
from importlib import import_module
import os
from flask import Flask, render_template, Response
import cv2
# Raspberry Pi camera module (requires picamera package)
video = cv2.VideoCapture(0)
if video is None:
    print ("Couldn't open camera...")
    exit(0)

def GetJpegFrame(vcap=video):
    suc, img=vcap.read()
    if not suc:
        print ("Get image error")
        return None
    ret, jpg = cv2.imencode('.jpg', img)
    print ("cam get img:", img.shape)
    return jpg.tobytes() 


# from camera_pi import Camera
app = Flask(__name__)
def gen(video):
    """Video streaming generator function."""
    while True:
        frame = GetJpegFrame(video)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
@app.route('/')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(video),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081, threaded=True)
