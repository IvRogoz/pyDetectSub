import cv2
import numpy as np
import pytesseract as tess

import sys

from subprocess import PIPE, Popen

from time import sleep
# VARIABLES
TEXT_TOP = 620
TEXT_BOTTOM = 678
TEXT_LEFT = 110
TEXT_RIGHT = 1192
SAMPLING_FRAME_COUNT = 60
SCENE_CHANGE_PERCENTAGE = 50
width, height = 1082, 58
count = 0
count_sub_start = 0
max_diff = 0
found = False
progress_bar = ""
(x, y, w, h) = (0, 0, 0, 0)
ar_old = 1
crWidth_old = 1
count_contours = 0


# Functions
def create_blank(width, height):
    """Create new image(numpy array) filled with certain color in RGB"""
    # Create black blank image
    image = np.zeros((height, width), np.uint8)

    # Since OpenCV uses BGR, convert the color first
    # color = tuple(reversed(rgb_color))
    # Fill image with color
    image[:] = 0

    return image


def update_progress(progress, total):
    percents = 100 * (progress / float(total))
    filled_length = int(round(100 * progress / float(total)))
    sys.stdout.write(
        '\r[\033[1;34mINFO\033[0;0m] [\033[0;32m{0}\033[0;0m] Buffering:{1}%'.format('#' * (filled_length / 5),
                                                                                     filled_length))
    if progress == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


def cmdline(command):
    process = Popen(
        args=command,
        stdout=PIPE,
        shell=True
    )
    return process.communicate()[0]


# Start Of Script
print(tess.get_tesseract_version())
print(tess.get_languages())

cap = cv2.VideoCapture('test_zh.mp4')
fps = cap.get(cv2.CAP_PROP_FPS)
sleep_ms = int(np.round((1 / fps) * 1000))

ret, current_frame = cap.read()
previous_frame = current_frame
height_frame, width_frame = current_frame.shape[:2]
window_pos_x = width_frame
window_pos_y = height_frame

# Init ROI_OLD Variable
roi_old = create_blank(width, height)
dst = create_blank(width, height)

# Play Video File
while (cap.isOpened()):
    if not ret:
        break
    # As subtitles are mostly fixed in position to reduce processing of Images we crop out the area where Subtitles should be   
    cropped_current = current_frame[TEXT_TOP:TEXT_BOTTOM, TEXT_LEFT:TEXT_RIGHT]
    cropper_previous = previous_frame[TEXT_TOP:TEXT_BOTTOM, TEXT_LEFT:TEXT_RIGHT]
    current_frame_gray = cv2.cvtColor(cropped_current, cv2.COLOR_BGR2GRAY)
    previous_frame_gray = cv2.cvtColor(cropper_previous, cv2.COLOR_BGR2GRAY)

    # Extract Subtitle Area from Cropped Image
    roi = cropped_current

    current_height, current_width = current_frame_gray.shape[:2]

    image_data = np.asarray(current_frame_gray)
    old_image_data = np.asarray(previous_frame_gray)

    image_data2 = cv2.inRange(image_data, (150), (255))
    old_image_data2 = cv2.inRange(image_data, (150), (255))

    dst = cv2.addWeighted(image_data2, 0.3, old_image_data2, 0.7, 0)

    mse_diff = np.concatenate((image_data2, dst, old_image_data2), axis=0)
    cv2.imshow("Pixels", mse_diff)

    boxes = tess.image_to_boxes(mse_diff)
    print(len(boxes.splitlines()))
    # dst = create_blank(current_width, current_height)

    # Resize ROI old to proper dimensions as konvolutions eat up pixels
    # roi_old = cv2.resize(roi_old,(current_width, current_height), interpolation = cv2.INTER_LINEAR)

    # Save current frame to old so it can be used in next iteration to detect changes
    # roi_old = dst

    # Show non edited Video feed
    cv2.putText(current_frame, "Frame:" + str(count), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255)
    cv2.imshow('Movie', current_frame)
    # cv2.moveWindow('Movie', 0, 0)

    # Increase Frame counter
    count = count + 1
    sleep(sleep_ms*0.001)

    # Wait q key to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    if count % 5 == 0:
        previous_frame = current_frame.copy()
    ret, current_frame = cap.read()

cap.release()
sys.exit(0)