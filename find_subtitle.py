import cv2
import os
import sys
import imutils
import argparse
import numpy as np
import pytesseract
from PIL import Image
from imutils import contours
from functools import reduce
from termcolor import colored
from subprocess import PIPE, Popen

# SUBTITLE POSITION IN VIDEO
TEXT_TOP = 425
TEXT_BOTTOM = 600
TEXT_LEFT = 5
TEXT_RIGHT = 700

# DETECTION VARIABLES
SAMPLING_FRAME_COUNT = 60
SCENE_CHANGE_PERCENTAGE = 5000
FOUND_START = False
SEARCH_END = False
RECT_ASPECT_RATIO = 3
CR_WIDTH = 0.25
ERODE = True
THRESHOLD_RED = 150
THRESHOLD_GREEN = 150
THRESHOLD_BLUE = 150
OUTPUT_FILE = ""

# GENERAL VIDEO VARIABLES
frame_count = 0 
start_frame_count = 0
count_sub_start = 0
count_contours = 0
count_subtitles = 0
start_frame = 0
progress_bar = ""

TESSERACT_LNG = "hrv"


# MISC - NEEDED ?
width, height = 450, 82
(x, y, w, h) = (0, 0, 0, 0)

# Functions
def create_blank(width, height):
    """Create new image(numpy array) filled with certain color in RGB"""
    # Create black blank image
    image = np.zeros((height, width), np.uint8)

    # Since OpenCV uses BGR, convert the color first
    #color = tuple(reversed(rgb_color))
    # Fill image with color
    image[:] = 0

    return image

def update_progress(progress, total):
    percents = 100 * (progress / float(total))
    filled_length = int(round(100 * progress / float(total)))
    sys.stdout.write('\r[\033[1;34mINFO\033[0;0m] [\033[0;32m{0}\033[0;0m] Buffering:{1}%'.format('#'* int(filled_length/5), filled_length))
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

def update_time(seconds):
    rediv = lambda ll,b : list(divmod(ll[0],b)) + ll[1:]
    return "%d:%02d:%02d,%03d" % tuple(reduce(rediv,[[seconds*1000,],1000,60,60]))


def get_sec(time_str):
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + int(s)

# Start Of Script


# Print Video Size
# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-t", "--threshold", help="Number of pixels offrame change to flag as new scene. Default is 5000", default = SCENE_CHANGE_PERCENTAGE, type=int)
ap.add_argument("-e", "--erode", help='Use cleanup function on found subtitles. Default is 0 or True, Off is 1', type=int)
ap.add_argument("-c", "--colors", help='Threshold for GBR Channels. Default is 150, Syntax "150,150,150"', type=str)
ap.add_argument("-b", "--buffer", help="Number of frames to buffer. Default is 60", default = SAMPLING_FRAME_COUNT, type=int)
ap.add_argument("-a", "--aspect", help="Aspect ratio for detection and filtering of rectangle contours used to detect subtitles. Default is 3", default = RECT_ASPECT_RATIO, type=int)
ap.add_argument("-w", "--width", help="Minimal width of subtitle rectangle. Default is 0.25", default = CR_WIDTH, type=float)
ap.add_argument("-p","--position", help='Position of fixed rectangle subtitle position in video. Syntax: "Top,Bottom,Left,Right"', type=str)
ap.add_argument("-o", "--output", help="Output results to file")
ap.add_argument("-l", "--lang", help="Setup Tesseract language. Default is hrv")
ap.add_argument("-s","--start", help='Start from time index. Syntax: "hh:mm:ss"', type=str)
ap.add_argument("-f", "--file", required=True, help="Path to video file")
args = vars(ap.parse_args())
args_r = ap.parse_args()

SCENE_CHANGE_PERCENTAGE = args_r.threshold
SAMPLING_FRAME_COUNT = args_r.buffer
RECT_ASPECT_RATIO = args_r.aspect
CR_WIDTH = args_r.width
if args_r.position:
    my_list = [int(item) for item in args_r.position.split(',')]
    TEXT_TOP = my_list[0]
    TEXT_BOTTOM = my_list[1]
    TEXT_LEFT = my_list[2]
    TEXT_RIGHT = my_list[3]

if args_r.start:
    start_frame = get_sec(args_r.start)

if args_r.colors:    
    my_list_c = [int(item) for item in args_r.colors.split(',')]
    THRESHOLD_RED = my_list_c[0]
    THRESHOLD_BLUE = my_list_c[1]
    THRESHOLD_GREEN = my_list_c[2]

if args_r.lang:
    TESSERACT_LNG = args_r.lang

if args_r.erode:
    if args_r.erode == 1:
        ERODE = False
    else:
        ERODE = True

OUTPUT_FILE = args_r.output

# Read Video File
FILE_NAME = args["file"]
cap = cv2.VideoCapture(FILE_NAME)
fps = cap.get(cv2.CAP_PROP_FPS)

cap.set(cv2.CAP_PROP_POS_FRAMES,start_frame * fps)

ret, current_frame = cap.read()


previous_frame = current_frame
height_frame, width_frame = current_frame.shape[:2]
window_pos_x = width_frame
window_pos_y = height_frame

# Init ROI_OLD Variable
out_image_old = create_blank(width, height)
t_old = create_blank(width, height)

print (colored("[INFO] Starting OpenCV operations","yellow"))
print ("[" + colored("INFO", 'blue') +"] Start Time: " + colored(str(args_r.start), 'green'))
print ("[" + colored("INFO", 'blue') +"] Video Size: " + colored(str(width_frame) + ":" + str(height_frame), 'green'))
print ("[" + colored("INFO", 'blue') +"] Video FPS: " + colored(str(fps), 'green'))
print ("[" + colored("INFO", 'blue') +"] Fixed Subtitle Position: " + colored("Top:" + str(TEXT_TOP) + " Bottom:" + str(TEXT_BOTTOM) + " Left:" + str(TEXT_LEFT) + " Right:" + str(TEXT_RIGHT),'green'))
print ("[" + colored("INFO", 'blue') +"] Buffer size: " + colored(str(SAMPLING_FRAME_COUNT), 'green') + " Frames")
print ("[" + colored("INFO", 'blue') +"] Threshold: " + colored(str(SCENE_CHANGE_PERCENTAGE) + " pixels",'green'))
print ("[" + colored("INFO", 'blue') +"] Erode: " + colored(str(ERODE) ,'green'))
print ("[" + colored("INFO", 'blue') +"] Aspect Ratio: " + colored(str(RECT_ASPECT_RATIO),'green'))
print ("[" + colored("INFO", 'blue') +"] Min Rectangle width: " + colored(str(CR_WIDTH),'green'))
print ("[" + colored("INFO", 'blue') +"] BGR Cutoff values: " + colored(str(THRESHOLD_BLUE),'blue') + ":" + colored(str(THRESHOLD_GREEN),'green') + ":" + colored(str(THRESHOLD_RED),'red'))
if OUTPUT_FILE:
    print ("[" + colored("INFO", 'blue') +"] Output Results to: " + colored(OUTPUT_FILE,'green'))
print ("[" + colored("INFO", 'blue') +"] Tesseract Language: " + colored(TESSERACT_LNG ,'green'))
print (colored("[INFO] Tesseract OCR Info:","yellow"))
print (cmdline('tesseract -v'))
print ("[" + colored("INFO", 'blue') +"] Starting search for subtitles: \n")

# initialize a rectangular and square structuring kernel
rectKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25,7)) # 13 5
sqKernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10)) #21 21   -  32 32
end_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 4)) #21 21   -  32 32

# Output Results
if OUTPUT_FILE:
    file = open(OUTPUT_FILE,'w') 

# Play Video File
while(cap.isOpened()):
    try:
        # As subtitles are mostly fixed in position to reduce processing of Images we crop out the area where Subtitles should be   
        cropped_current = current_frame[TEXT_TOP:TEXT_BOTTOM, TEXT_LEFT:TEXT_RIGHT]    
    except:
        print (colored("\nDone...", "yellow"))
        break
    
    # Extract Subtitle Area from Cropped Image

    # Cut BGR values to set up threshold of 150
    white_region = cv2.inRange(cropped_current, (int(THRESHOLD_BLUE),int(THRESHOLD_GREEN),int(THRESHOLD_RED)), (255,255,255))
            
    # Perform erode and closing
    if ERODE:
        se1 = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        se2 = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
        mask = cv2.morphologyEx(white_region, cv2.MORPH_CLOSE, se1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, se2)
        mask = np.dstack([mask, mask, mask]) / 255
        out_image = cropped_current * mask
        out_image = np.array(out_image, dtype=np.uint8)
        out_image = cv2.cvtColor(out_image, cv2.COLOR_BGR2GRAY)
    else:
        out_image = white_region
           
    current_height, current_width = out_image.shape[:2]

    # Resize ROI old to proper dimensions as konvolutions eat up pixels
    out_image_old = cv2.resize(out_image_old,(current_width, current_height), interpolation = cv2.INTER_LINEAR)
            
    # Weighted add up old and new ROI 
    dst = cv2.addWeighted(out_image,0.5,out_image_old,0.5,0) 
    out_image_old = dst           

    # Start of operations to determine the Aspect ratio and width of Subtitles
    # This is used together with Diff to detect scene change

    # apply a closing operation using the rectangular kernel to help
    # cloes gaps in between characters
    gradX = cv2.morphologyEx(dst, cv2.MORPH_CLOSE, rectKernel)
    thresh = cv2.threshold(gradX, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # apply a second closing operation to the binary image, again
    # to help close gaps 
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, sqKernel)

    # calculate the difference and its norms
    t_height, t_width = thresh.shape[:2]
    t_old = cv2.resize(t_old,(t_width, t_height), interpolation = cv2.INTER_LINEAR)

    t_test = thresh - t_old
    count_white = cv2.countNonZero(t_test);
    count_white_thresh = cv2.countNonZero(thresh)

    # Show Frame Differences
    mse_diff = np.concatenate((dst, thresh, t_test, t_old), axis=0)

    cv2.putText(mse_diff,"Frame:"+str(update_time(frame_count/fps)), (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255)
    cv2.putText(mse_diff,"Diff :"+str(count_white), (10,100), cv2.FONT_HERSHEY_SIMPLEX, 1, 255)
    cv2.putText(mse_diff,"White:"+str(count_white_thresh), (10,150), cv2.FONT_HERSHEY_SIMPLEX, 1, 255)
    cv2.imshow("Diff", mse_diff)
    cv2.moveWindow('Diff', window_pos_x, 0)

    # Save Current frame as Old Frame
    t_old = thresh

    # Find Contours
    cnts_org, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # cnts_org = if imutils.is_cv2() else cnts_org[1]
    cnts = sorted(cnts_org, key=cv2.contourArea, reverse=True)

    # loop over the contours
    for c in cnts:
        # compute the bounding box of the contour and use the contour to
        # compute the aspect ratio and coverage ratio of the bounding box
        # width to the width of the image
        (x, y, w, h) = cv2.boundingRect(c)
        ar = w  // float(h)
        crWidth = round(w / float(dst.shape[1]),2)

        # Grow bounding box as it was eroded before
        pX = int((x + w) * 0.05)
        pY = int((y + h) * 0.15)
        (x, y) = (x - pX, y - pY)
        (w, h) = (w + (pX * 2), h + (pY * 2))

        # Reset contour related variables before next frame
        # Test for proper Aspect Ratio and width of subtitles
        if ar > RECT_ASPECT_RATIO and crWidth > CR_WIDTH:
            cv2.rectangle(cropped_current, (x, y), (x + w, y + h), (0, 255, 0), 2) # Show contour in main Window
            count_contours +=1 # Count contours

    # Detect Scene change
    if count_white > SCENE_CHANGE_PERCENTAGE and not FOUND_START and not SEARCH_END and count_white_thresh > 0: # and count_contours > 0:        
        count_sub_start = frame_count
        print ("[" + colored("INFO", 'blue') +"]" + colored(" FOUND SUBTITLE: ", 'green') + colored(str(int(count_white)) + " Pixels", 'red') + colored(" @ FRAME ", 'green') + colored(str(frame_count),'red'))
        dst = create_blank(width, height)
        FOUND_START = True
        SEARCH_END = False

    # Update progress bar
    if FOUND_START:
        update_progress(frame_count - count_sub_start, SAMPLING_FRAME_COUNT)


    # MAIN PART - ALL PREPROCESSING IS DONE
    # dst image var containes all image info
    if FOUND_START and (frame_count - count_sub_start == SAMPLING_FRAME_COUNT) and not SEARCH_END:
        cv2.imshow("To Tesseract", dst)
        #dst = create_blank(width, height)
        print ("[" + colored("INFO", 'blue') + "] " + colored('Waiting for tesseract OCR: ', 'red')) #+ colored("SKIPPED", 'yellow')
        gig = cv2.morphologyEx(dst, cv2.MORPH_CLOSE, end_kernel)
        gig2 = imutils.resize(gig, height=300)
        to_tesseract = Image.fromarray(gig2)
        text = pytesseract.image_to_string(to_tesseract, lang=TESSERACT_LNG)
        print(text)
        if OUTPUT_FILE:
            start_frame_count = frame_count

        #print ""
        FOUND_START = False
        SEARCH_END = True

    if (not FOUND_START and SEARCH_END and count_white > SCENE_CHANGE_PERCENTAGE and (frame_count - count_sub_start > SAMPLING_FRAME_COUNT)) and count_white_thresh < SCENE_CHANGE_PERCENTAGE:
        print ("[" + colored("INFO", 'blue') + "] " + colored('FOUND SUBTITLE END', 'red') + colored(" @ FRAME ", 'green') + colored(str(frame_count),'red') + "\n")
    
        if OUTPUT_FILE:
            count_subtitles += 1
            file.write(str(count_subtitles)+ "\n")
            file.write(update_time((start_frame_count - SAMPLING_FRAME_COUNT)/fps) + " --> " + update_time(frame_count/fps) +"\n")
            file.write(text + "\n") 
            file.write("\n") 
        FOUND_START = False
        SEARCH_END = False

    # Show non edited Video feed
    cv2.putText(current_frame,"Frame:"+str(frame_count), (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1, 255)
    cv2.rectangle(current_frame, (TEXT_LEFT, TEXT_TOP), (TEXT_RIGHT, TEXT_BOTTOM), (0, 0, 255), 2) 
    cv2.imshow('Movie',current_frame)   
    cv2.moveWindow('Movie', 0, 0)

    # Increase Frame counter
    frame_count = frame_count + 1
    count_contours = 0
    # Wait q key to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    try:
        ret, current_frame = cap.read()    
    except :
        print(colored("End...", "yellow"))
    
if OUTPUT_FILE:
    file.close() 
cap.release()