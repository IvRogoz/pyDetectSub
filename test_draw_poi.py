import cv2
from time import sleep
import sys
import queue
# from ffpyplayer.player import MediaPlayer
import numpy

name = 'Movie'
sourcePath = 'test_zh.mp4'

cap = cv2.VideoCapture(sourcePath)
fps = cap.get(cv2.CAP_PROP_FPS)
sleep_ms = int(numpy.round((1 / fps) * 1000))
ret, current_frame = cap.read()
font = cv2.FONT_HERSHEY_SIMPLEX
xy = queue.Queue(2)
# player = MediaPlayer(sourcePath)
def click_event(event, x, y, flags, params):
    # checking for left mouse clicks
    if event == cv2.EVENT_LBUTTONDOWN:

        print(x, ' ', y)
        xy.put(('l', x, y))

    # checking for right mouse clicks
    if event == cv2.EVENT_RBUTTONDOWN:

        print(x, ' ', y)
        xy.put(('r', x, y))



while (cap.isOpened()):
    # audio_frame, val = player.get_frame()

    sleep(sleep_ms*0.001)
    # Wait q key to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    if xy.empty() == False:

        for i in range(xy.qsize()):

            item = xy.get()
            if item[0] == 'l':
                cv2.putText(current_frame, str(item[1]) + ',' +
                            str(item[2]), (item[1], item[2]), font,
                            0.5, (255, 0, 0), 1)
            elif item[0] == 'r':
                cv2.putText(current_frame, str(item[1]) + ',' +
                            str(item[2]), (item[1], item[2]), font,
                            0.5, (255, 255, 0), 1)

    cv2.imshow(name, current_frame)
    cv2.setMouseCallback(name, click_event)
    ret, current_frame = cap.read()


cap.release()
sys.exit(0)