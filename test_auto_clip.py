import time
from datetime import datetime
import pysrt
import cv2

clip_offset_frame = 4
def srt_object_to_seconds(srt_time):
    # Calculate the total time duration in seconds
    total_seconds = (
        srt_time.hours * 3600 +
        srt_time.minutes * 60 +
        srt_time.seconds +
        srt_time.milliseconds / 1000
    )

    return total_seconds
def process_srt_file(file_path):

    subs = pysrt.open(file_path)

    time_differences = []

    # for i in range(len(subtitle_entries) - 1):
    #     subtitle1_start_time = subtitle_entries[i]["start_time"]
    #     subtitle1_end_time = subtitle_entries[i]["end_time"]
    #     subtitle2_start_time = subtitle_entries[i + 1]["start_time"]
    #     subtitle2_end_time = subtitle_entries[i + 1]["start_time"]
    #
    #     time_difference = subtract_subtitle_times(subtitle1_end_time, subtitle2_start_time)
    #     format_string = "%H:%M:%S,%f"  # Format string for SRT time format
    #     # if time_difference <=200:
    #
    #     # Convert the time difference to milliseconds
    #     seconds = time_difference / 1000
    #     time_differences.append(
    #         {'start_time': time_to_seconds(subtitle1_start_time), 'end_time': time_to_seconds(subtitle2_end_time),
    #          'seconds': seconds})
    previous = 0
    for i in range(len(subs) - 1):
        subtitle1_start_time = subs[i].start
        subtitle1_end_time = subs[i].end
        subtitle2_start_time = subs[i + 1].start
        subtitle2_end_time = subs[i + 1].start

        time_difference = subtitle2_start_time - subtitle1_end_time

        seconds = srt_object_to_seconds(time_difference)
        time_differences.append({'start_time': srt_object_to_seconds(subtitle1_start_time), 'end_time': srt_object_to_seconds(subtitle1_end_time), 'seconds': seconds})
        previous = seconds
    return time_differences


# Example usage
srt_file_path = "combine_output.srt"

subs = process_srt_file(srt_file_path)

cap = cv2.VideoCapture('test_zh.mp4')
fps = 25
count = 0
start_frame = 0
frame_duration = 1 / fps
for i, subtitle in enumerate(subs):
    start_time = subtitle['start_time']
    end_time = subtitle['end_time']

    tmp_end = 0
    output_width, output_height = (
        int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    )

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_path = 'clipped_video_'+str(count)+'.mp4'
    output_video = cv2.VideoWriter(output_path, fourcc, fps, (output_width, output_height))

    # frame_count = start_frame
    start_frame = start_time * fps
    end_frame = end_time * fps

    print('start_frame'+ str(start_frame))
    print('end_frame' + str(end_frame))
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)


    frame_count = 0
    while frame_count < end_frame-start_frame:
        ret, frame = cap.read()
        if not ret:
            break
        output_video.write(frame)
        # Adjust frame rate if necessary
        # if frame_duration > 0:
        #     cv2.waitKey(int(frame_duration * 1000))  # Delay between frames
        # time.sleep(frame_duration)
        frame_count += 1
    # start_frame = start_frame + frame_count
    print('clipped_video_<'+str(count)+'----'+str(end_frame)+'>.mp4'+'  finished!')
    count += 1


output_video.release()
cap.release()

