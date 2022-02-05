#!/usr/bin/env python
from importlib import import_module
import os, copy
import os.path as op
from flask import Flask, render_template, Response
import cv2, datetime
import numpy as np
import threading

dt_ms = lambda: datetime.datetime.now().strftime(
    '%Y-%m-%d_%H:%M:%S.%f')  # 含微秒的日期时间2018-09-06_21:54:46.205213

# Raspberry Pi camera module (requires picamera package)
video = cv2.VideoCapture(0)
if video is None:
    print("Couldn't open camera...")
    exit(0)
'''
video.set(cv2.CAP_PROP_FRAME_WIDTH, 1080)#宽度
video.set(cv2.CAP_PROP_FRAME_HEIGHT, 960)#高度
video.set(cv2.CAP_PROP_FPS, 30)#帧率 帧/秒
video.set(cv2.CAP_PROP_BRIGHTNESS, 1)#亮度 1
video.set(cv2.CAP_PROP_CONTRAST,40)#对比度 40
video.set(cv2.CAP_PROP_SATURATION, 50)#饱和度 50
video.set(cv2.CAP_PROP_HUE, 50)#色调 50
video.set(cv2.CAP_PROP_EXPOSURE, 50)#曝光 50
'''
'''
video.get(cv2.CAP_PROP_FRAME_WIDTH)
video.get(cv2.CAP_PROP_FRAME_HEIGHT)
video.get(cv2.CAP_PROP_FPS)
video.get(cv2.CAP_PROP_BRIGHTNESS)
video.get(cv2.CAP_PROP_CONTRAST)
video.get(cv2.CAP_PROP_SATURATION)
video.get(cv2.CAP_PROP_HUE)
video.get(cv2.CAP_PROP_EXPOSURE)
'''

frame_w = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
vfps = video.get(cv2.CAP_PROP_FPS)

STOREADDR = './cutvideos'
os.makedirs(STOREADDR, exist_ok=True)

threadLock = threading.Lock()
maxlistlen = 10
frame_list = []


def GetJpegFrame(vcap):
    suc, img = vcap.read()
    if not suc:
        print("Get image error")
        return None
    #print ("cam get img:", img.shape)
    return img


def GetJpegBytes(img):
    ret, jpg = cv2.imencode('.jpg', img)

    return jpg.tobytes()


def pHash(img):
    """
    get image pHash value
    """

    # 缩放图片为32x32灰度图片
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img = cv2.resize(img, (32, 32), interpolation=cv2.INTER_CUBIC)

    # 创建二维列表
    h, w = img.shape[:2]
    vis0 = np.zeros((h, w), np.float32)
    vis0[:h, :w] = img

    # 二维Dct变换
    vis1 = cv2.dct(cv2.dct(vis0))
    vis_len=12
    vis1 = vis1[:vis_len, :vis_len]

    # 把二维list变成一维list
    img_list = vis1.flatten().tolist()

    # 计算均值, 得到哈希值
    avg = np.mean(img_list)
    avg_list = [0 if i < avg else 1 for i in img_list]
    # print(avg_list)
    return avg_list


def hanming_dist(s1, s2):
    """
    求汉明距离
    """
    # print(s1, s2)
    return sum([ch1 != ch2 for ch1, ch2 in zip(s1, s2)])


def IsDiff(frame1, frame2, thresh=50) -> bool:
    phash1 = pHash(frame1)
    phash2 = pHash(frame2)
    hamdis = hanming_dist(phash1, phash2)
    # print("hamdis: ", hamdis)
    return hamdis > thresh


# use flask to watch video
app = Flask(__name__)


def gen(video):
    """Video streaming generator function."""
    while True:
        frame = b''
        threadLock.acquire()
        if len(frame_list) > 0:
            frame = copy.deepcopy(frame_list[-1])
        threadLock.release()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def video_feed():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen(video),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


class CutThread(threading.Thread):

    def __init__(self, thresh_pixel=50, thresh_lenth_time_s=5):
        threading.Thread.__init__(self)
        self.thresh_pixel = thresh_pixel
        self.stop = False
        self.thresh_lenth_time_s = thresh_lenth_time_s

    # fun to find moving action in video to save video
    def run(self):
        print("Begin cut thread...")
        vid = None
        lastframe = None
        vname = ''
        videolen = 0

        while not self.stop:
            img = GetJpegFrame(video)
            if img is None:
                continue
            img_bytes = GetJpegBytes(img)

            # thread op lock
            threadLock.acquire()

            frame_list.append(img_bytes)
            if len(frame_list) > maxlistlen:
                del frame_list[0:len(frame_list) - maxlistlen]  #删除,不包括尾部元素

            threadLock.release()

            if lastframe is not None:
                if (vid is not None and
                        videolen / vfps <= self.thresh_lenth_time_s) or IsDiff(
                            lastframe, img, self.thresh_pixel):
                    if vid is None:
                        fourcc = cv2.VideoWriter_fourcc(
                            *'XVID')  #  *'MJPG'    *'FLV1'
                        vname = op.join(STOREADDR, dt_ms()) + ".avi"
                        vid = cv2.VideoWriter(vname, fourcc, vfps,
                                              (frame_w, frame_h), True)
                        videolen = 0
                        print("New video: ", vname)
                    vid.write(img)
                    videolen += 1
                else:
                    if vid is not None:
                        vid.release()
                        vid = None
                        print("Video %s finished" % vname)
            lastframe = img
        print("Cut thread stoped...")

    def stopthread(self):
        print("Stoping cut thread...")
        self.stop = True


if __name__ == '__main__':
    thre = CutThread(6, 5)
    thre.start()

    try:
        app.run(host='0.0.0.0', port=8080, threaded=True)
    except:
        pass
    finally:
        thre.stopthread()
        video.release()
        thre.join()
