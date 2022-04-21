# coding=utf-8

import cv2

from io import BytesIO
import time
import threading
from flask import Flask, render_template, Response

import lib_mipicam.D_mipicamera as Dcam
from ctypes import byref
import sys



outputFrame = None
condition = threading.Condition()
loginfo = 'running'



app = Flask(__name__)




class mipi_camera_ex(Dcam.mipi_camera):
    def init_camera(self,camera_interface=None,videofmt = None):
        cam_infe = Dcam.CAMERA_INTERFACE(0,-1,(0,0),(0,0))
        if camera_interface is not None:
            try:
                cam_infe.i2c_bus, cam_infe.camera_num, (cam_infe.sda_pins[0], cam_infe.sda_pins[1]), (cam_infe.scl_pins[0], cam_infe.scl_pins[1]) = camera_interface
            except (TypeError, ValueError) as e:
                raise TypeError(
                    "Invalid camera_interface " )
        Dcam.check_status(
            Dcam.D_init_camera_ex(byref(self.camera_instance), cam_infe, videofmt),
            sys._getframe().f_code.co_name
            )
            


@app.route('/')
def index():
    global loginfo
    """Video streaming home page."""
    return render_template('index.html', loginfo = loginfo)


def get_frame(cam):
    global outputFrame
    while True:
        try:
            frame = cam.capture(encoding = 'jpeg')
            #with lock:
            with condition:
                outputFrame = frame.as_array.tobytes()
                condition.notify_all()
            cam.release_buffer(frame)



        except Exception as e:
            loginfo = 'error, %s. \r\n\r\n Try again in %s seconds.' % (e, str(2))
            print(loginfo)
            time.sleep(2)
            pass


def generate():
    """Video streaming generator function."""

    global outputFrame

    while True:
        with condition:
            condition.wait()
            # if outputFrame is None:
            #     continue
            encodedImage = outputFrame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: '+ bytes(str(len(encodedImage)),encoding='utf-8') + b'\r\n'
               b'\r\n' +
               encodedImage + b'\r\n')


@app.route('/video_feed')
def video_feed():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":


    print("Open camera...")
    camera = mipi_camera_ex()
    videofmt = Dcam.FORMAT(width=1280,height=720,framerate=60)
    camera.init_camera(camera_interface = (0,-1,(0,0),(0,0)),videofmt = videofmt)
    print("start streaming...")
    t1 = threading.Thread(target=get_frame,args=(camera,))
    t1.daemon = True
    t1.start()
    app.run(host='0.0.0.0', threaded=True, debug=True, port="8080", use_reloader=False)
