import os
import sys
import cv2
import time
import imutils
from art import *
import argparse
import pytesseract
import numpy as np
from PIL import Image
from functools import reduce
from termcolor import colored
from subprocess import PIPE, Popen

TESSERACT_LNG = "hrv"   # Default tesseract language to use. Change to eng for english or use cmd switch -l
DETECTION_TYPE = 0      # Detection methods, 0 is total diff, 1 is more selective, cmd switch -d
DETECTION_TYPE_TEXT = "detection based on Total percentage changed"

# GENERAL VIDEO VARIABLES
frames = 0              # variable that holds total number of frames processed
START_FRAME = 0         # Start from which frame, use cmd switch -s
OUTPUT_FILE = ""        # Write subtitle to what file. Add using cmd switch -o
(W, H) = (None, None)

# SUBTITLE POSITION IN VIDEO
TEXT_TOP = 425          # top default value to start CROP, use cmd switch -p to set 
TEXT_BOTTOM = 600       # bottom default value to start CROP
TEXT_LEFT = 5           # left default value to start CROP
TEXT_RIGHT = 700        # right default value to start CROP
found_start = False     # found start of subtitle
found_end = False       # found end of subtitle
found_start_frame = 0   # subtitle found at frame
found_end_frame = 0     # subtitle end found at frame 
count_subtitles = 0     # Current subtitle number
no_contours = 0         # how many contours are visible on screen that are big enough to contain subtitle
(x, y, w, h) = (0, 0, 0, 0) # misc attributes for contours

# Provides console progress bar
def update_progress(progress, total): 
    percents = 100 * (progress / float(total))
    filled_length = int(round(100 * progress / float(total)))
    sys.stdout.write('\r[\033[1;34mINFO\033[0;0m] [\033[0;32m{0}\033[0;0m] Progress:{1}%'.format('#'* int(filled_length/5), filled_length))
    if progress == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

# Execute cmd in shell and returns output
def cmdline(command):
    process = Popen(
        args=command,
        stdout=PIPE,
        shell=True
    )
    return process.communicate()[0]

# functions used to calculate time from frames
def update_time(seconds):
    rediv = lambda ll,b : list(divmod(ll[0],b)) + ll[1:]
    return "%d:%02d:%02d,%03d" % tuple(reduce(rediv,[[seconds*1000,],1000,60,60]))

def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)    


# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-v", "--video", type=str, help="path to input video file")
ap.add_argument("-o", "--output", help="Output results to file")
ap.add_argument("-l", "--lang", help="Setup Tesseract language. Default is hrv")
ap.add_argument("-s","--start", help='Start from time index. Syntax: "hh:mm:ss"', type=str)
ap.add_argument("-p","--position", help='Position of fixed rectangle subtitle position in video. Syntax: "Top,Bottom,Left,Right"', type=str)
ap.add_argument("-t", "--threshold", type=float, default=1,	help="minimum probability of region to be classified as text")
ap.add_argument("-d", "--detect", type=int, default=0, help="0: detection based on Total percentage changed, 1: detection based on word count change and template")
args = vars(ap.parse_args())
args_r = ap.parse_args()

os.system('cls')
print()
tprint("DetectSubTitles", font="nancyj-fancy") 
print("by Ivan Rogoz")
print()

if len(sys.argv)==1:
    # display help message when no args are passed.
    ap.print_help()
    sys.exit(1)

if args_r.start:
    START_FRAME = get_sec(args_r.start)

if args_r.position:
    my_list = [int(item) for item in args_r.position.split(',')]
    TEXT_TOP = my_list[0]
    TEXT_BOTTOM = my_list[1]
    TEXT_LEFT = my_list[2]
    TEXT_RIGHT = my_list[3]

if args_r.lang:
    TESSERACT_LNG = args_r.lang

if args_r.output:
    OUTPUT_FILE = args_r.output
    file = open(OUTPUT_FILE,'w', encoding="utf-8") 

if args_r.detect:
    DETECTION_TYPE = args_r.detect

print ("[" + colored("INFO", 'red') +"] Starting OpenCV operations ")
SCEME_CHANGE = args_r.threshold

FILE_NAME = args["video"]
cap = cv2.VideoCapture(FILE_NAME)
print ("[" + colored("INFO", 'blue') +"] starting video stream for "+colored(args_r.video,'green'))

fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))/2
print ("[" + colored("INFO", 'blue') +"] Video FPS: " + colored(str(fps), 'green'))

cap.set(cv2.CAP_PROP_POS_FRAMES,START_FRAME * fps)
print ("[" + colored("INFO", 'blue') +"] Start Time (s): " + colored(str(START_FRAME * fps), 'green'))

ret, current_frame = cap.read() # Read first frame
height_frame, width_frame = current_frame.shape[:2] # get height and width of video, not used except to show the info 

# All of this should be revisited what is needed and what not. 
found_image = current_frame.copy() # Init found image variable 
found_image = found_image[TEXT_TOP:TEXT_BOTTOM, TEXT_LEFT:TEXT_RIGHT]  # Crop frame
found_image = imutils.resize(found_image, width=1000) # resize so we have uniform size moving forward
buffer_text_frame = cv2.cvtColor(found_image, cv2.COLOR_BGR2GRAY) # init buffer variable and make it grayscale
difference = current_frame # init difference variable to current frame 
next_frame = found_image # init next frame variable 

print ("[" + colored("INFO", 'blue') +"] Video Size: " + colored(str(width_frame) + ":" + str(height_frame), 'green'))
print ("[" + colored("INFO", 'blue') +"] Threshold: " + colored(str(SCEME_CHANGE) + "%",'green'))

if DETECTION_TYPE == 1:
    DETECTION_TYPE_TEXT = "detection based on word count change and template"
print ("[" + colored("INFO", 'blue') +"] Detection Type: " + colored(str(DETECTION_TYPE_TEXT),'green'))

if OUTPUT_FILE:
    print ("[" + colored("INFO", 'blue') +"] Output Results to: " + colored(OUTPUT_FILE,'green'))

print ("[" + colored("INFO", 'blue') +"] Tesseract Language: " + colored(TESSERACT_LNG ,'green'))
print ("[" + colored("INFO", 'blue') +"] Starting search for subtitles: \n")
sys.stdout.write('\n')


# loop over frames from the video stream
while(cap.isOpened()):
    ret, current_frame = cap.read() # Read next frame, prior read was to init variables
    if current_frame is None: # if there is frame continue if not break 
        print ("[" + colored("INFO", 'red') +"] Press q to quit")
        break

    cv2.imshow("Original", current_frame) # Shows original video without and modifications
	
    # resize the frame, maintaining the aspect ratio
    current_frame = current_frame[TEXT_TOP:TEXT_BOTTOM, TEXT_LEFT:TEXT_RIGHT] 
    current_frame = imutils.resize(current_frame, width=1000)

    if W is None or H is None:
        (H, W) = current_frame.shape[:2]

    # Create blank image to be used at subtitle detection end to clear text enhancment buffer
    blank = np.zeros((H, W, 1), np.uint8) 
    # Convert current frame to grayscale
    grayA = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY) 
    # Convert next frame to grayscale
    grayB = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY) 
    # Compare two frames using one frame as a template, used in second detection method
    template_diff = cv2.matchTemplate(grayA, grayB, cv2.TM_CCOEFF_NORMED) 
    # convert to percentage
    template_diff = abs(template_diff - 1) 
    # Main Part of background removal
    grayB = cv2.bitwise_not(grayB) # invert next frame 
    # Combine current frame and inverted next frame which removes background 
    # and only stationary pixels get selected
    difference = cv2.subtract(grayA, grayB) 
    # Calculate percentage of change over entire cropped region
    diff = (cv2.countNonZero(difference) / float(W * H)) * 100 
    # Part to remove any non white artefacts and find contours
    ret,thresh4 = cv2.threshold(difference,100,255,cv2.THRESH_BINARY)
    blurred = cv2.GaussianBlur(thresh4, (25, 25), 0)
    ret, gray = cv2.threshold(blurred, 0 , 255, cv2.CHAIN_APPROX_NONE)
    kernel = np.ones((15,15), np.uint8) 
    # Blow up text to make it easier to select contours of individual words instead of letters
    gray = cv2.dilate(gray, kernel) 
    # Invert Image before looking for contours
    gray = cv2.bitwise_not(gray) 
    # Find contours and remove third dimension of array
    contours, hierarchy = cv2.findContours(gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2:] 
    image_contour = np.copy(current_frame) # Create temp image
    # Draw contours on temp image
    cv2.drawContours(image_contour, contours, -1, (0, 255, 0), 2, cv2.LINE_AA, maxLevel=1) 

    cv2.putText(gray,"Diff Total:" +str("%5.2f" % diff) + "% -> Diff Contour:"+ 
        str("%5.2f" % (template_diff*10)) + 
        "%", (10,10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 2) 

    if DETECTION_TYPE == 0:
        if not found_start and diff >= SCEME_CHANGE:
            found_start = True
            found_end = False
            found_start_frame = frames
            
        elif diff <= SCEME_CHANGE and found_start:
            found_end = True
            found_start = False
            count_subtitles += 1
            found_end_frame = frames

            sys.stdout.write('\n')
            print ("[" + colored("INFO", 'blue') +"]" + colored(" SUBTITLE No.", 'green') +str(count_subtitles)+" @ "+colored(update_time(found_start_frame/fps) + " --> " + update_time(found_end_frame/fps),'yellow'))
            print ("[" + colored("INFO", 'blue') + "] " + colored('Waiting for tesseract OCR: ', 'red')) 

            to_tesseract = imutils.resize(buffer_text_frame, height=300)
            to_tesseract = Image.fromarray(to_tesseract)
            text = pytesseract.image_to_string(to_tesseract, lang=TESSERACT_LNG)
            print(text)
            if OUTPUT_FILE:
                file.write(str(count_subtitles)+ "\n")
                file.write(update_time(found_start_frame/fps) + " --> " + update_time(found_end_frame/fps) +"\n")
                file.write(text + "\n") 
                file.write("\n") 
                print ("[" + colored("INFO", 'green') +"] Text added to file " + OUTPUT_FILE)
                sys.stdout.write('\n')
            buffer_text_frame = blank.copy() # difference
        elif found_start :
            buffer_text_frame = cv2.add(difference, buffer_text_frame)
    
    elif DETECTION_TYPE == 1:
        no_contours = 0
        for (i,c) in enumerate(contours):
            (x,y,w,h) = cv2.boundingRect(c)
            if w > 80 and h > 30:
                no_contours += 1

        if not found_start and template_diff >= SCEME_CHANGE and no_contours > 0:
            found_start = True
            found_end = False
            found_start_frame = frames
        elif (template_diff >= SCEME_CHANGE) and found_start:
            found_end = True
            found_start = False
            count_subtitles += 1
            found_end_frame = frames

            sys.stdout.write('\n')
            print ("[" + colored("INFO", 'blue') +"]" + colored(" SUBTITLE No.", 'green') +str(count_subtitles)+" @ "+colored(update_time(found_start_frame/fps) + " --> " + update_time(found_end_frame/fps),'yellow'))
            print ("[" + colored("INFO", 'blue') + "] " + colored('Waiting for tesseract OCR: ', 'red')) 

            to_tesseract = imutils.resize(buffer_text_frame, height=300)
            to_tesseract = Image.fromarray(to_tesseract)
            text = pytesseract.image_to_string(to_tesseract, lang=TESSERACT_LNG)
            print(text)

            if OUTPUT_FILE:
                file.write(str(count_subtitles)+ "\n")
                file.write(update_time(found_start_frame/fps) + " --> " + update_time(found_end_frame/fps) +"\n")
                file.write(text + "\n") 
                file.write("\n") 
                print ("[" + colored("INFO", 'green') +"] Text added to file " + OUTPUT_FILE)
                sys.stdout.write('\n')

            buffer_text_frame = blank.copy()
        elif found_start :
            buffer_text_frame = cv2.add(difference, buffer_text_frame)

    # show the output frame
    grayImageBGRspace = cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)
    verticalAppendedImg = np.vstack((current_frame, grayImageBGRspace, cv2.cvtColor(buffer_text_frame, cv2.COLOR_GRAY2BGR), image_contour))
    cv2.imshow("Text Detection", verticalAppendedImg)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        sys.stdout.write('\n')
        print ("[" + colored("INFO", 'red') +"] Playback Stoped ")
        break
    try:
        ret, next_frame = cap.read()  
        if current_frame is None:
            sys.stdout.write('\n')
            print ("[" + colored("INFO", 'red') +"] Press q to quit ")
            break  
        next_frame = next_frame[TEXT_TOP:TEXT_BOTTOM, TEXT_LEFT:TEXT_RIGHT] 
        next_frame = imutils.resize(next_frame, width=1000)

        frames += 1
        update_progress(frames, total_frames-1)
    except :
            sys.stdout.write('\n')
            print ("[" + colored("INFO", 'red') +"] No Image or End of File ")

# close all windows
if cv2.waitKey() & 0xFF == ord('q'):
    cv2.destroyAllWindows()
    cap.release()
    sys.stdout.write('\n')
    print ("[" + colored("INFO", 'red') +"] END ")
