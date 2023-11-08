import os
import sys
import re
import datetime
from pydub import AudioSegment
from moviepy.editor import VideoFileClip
from datetime import timedelta

def ensure_mp3(input_file):
    filename, extension = os.path.splitext(input_file)
    if extension.lower() != ".mp3":
        if extension.lower() in [".wav", ".flv", ".flac", ".ogg", ".m4a"]:
            audio = AudioSegment.from_file(input_file)
            mp3_filename = filename + ".mp3"
            audio.export(mp3_filename, format="mp3")
            os.remove(input_file)
            return mp3_filename
        elif extension.lower() in [".mp4", ".mkv", ".flv", ".avi"]:
            video = VideoFileClip(input_file)
            audio = video.audio
            mp3_filename = filename + ".mp3"
            audio.write_audiofile(mp3_filename)
            video.close()  # Закрываем объект VideoFileClip
            os.remove(input_file)
            return mp3_filename
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {extension}")
    else:
        return mp3_filename

def diar_file(input_file, model):
    try:
        input_file = ensure_mp3(input_file)
        output_folder = os.path.dirname(input_file)
        output_file = os.path.join(output_folder, os.path.basename(input_file).replace(".mp3", "") + ".txt")
        segments, info = model.transcribe(input_file, beam_size=5, vad_filter=True, vad_parameters=dict(min_silence_duration_ms=20000, speech_pad_ms=0))
        results = []
        file_name = os.path.basename(input_file).replace(".mp3", "")
        for segment in segments:
            start_time = (datetime.datetime.min + timedelta(seconds=segment.start)).strftime('%H:%M:%S')
            end_time = (datetime.datetime.min + timedelta(seconds=segment.end)).strftime('%H:%M:%S')
            results.append("[%s -> %s] [%s] %s" % (start_time, end_time, file_name, segment.text) + "\n")
        if results:
            with open(output_file, "a", encoding="UTF-8") as f:
                f.writelines(results)
        os.remove(input_file)
        segments = None
        input_file = None

    except Exception as e:
        print(f"Ошибка при обработке файла {input_file}: {e}")
