import pysrt
from pysrt import SubRipFile

def combine_subtitles(subtitles):
    combined_subtitles = []
    current_subtitle = None

    for subtitle in subtitles:
        if current_subtitle is None:
            current_subtitle = subtitle
        else:
            time_gap = subtitle.start - current_subtitle.end
            if time_gap < 200:  # Adjust the threshold as per your requirement
                current_subtitle.text += ' ' + subtitle.text
                current_subtitle.end = subtitle.end
            else:
                combined_subtitles.append(current_subtitle)
                current_subtitle = subtitle

    if current_subtitle is not None:
        combined_subtitles.append(current_subtitle)

    return combined_subtitles

# Load the SRT file
subs = pysrt.open('test_zh1.srt')
combined_subs = combine_subtitles(subs)
subtitles = SubRipFile()
for sub in combined_subs:
    subtitles.append(sub)

subtitles.save('combine_output.srt')


