import threading
import time
import cv2
import numpy as np
import pyaudio
import wave
import mss
from modules.logger import log_info, log_error  # Logger propriu
import ffmpeg


# Înregistrare audio
class AudioRecorder:
    def __init__(self, duration=60, file_name="audio.wav"):
        self.sample_rate = 44100
        self.channels = 2
        self.duration = duration
        self.file_name = file_name
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False

    def find_blackhole_device(self):
        """Găsește dispozitivul BlackHole pentru înregistrare audio."""
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if "BlackHole" in device_info['name']:
                self.input_device_index = i
                log_info(f"Found BlackHole device: {device_info['name']}")
                return True
        log_info("BlackHole loopback device not found.")
        return False

    def save_audio(self):
        """Salvează înregistrarea audio într-un fișier."""
        with wave.open(self.file_name, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
        log_info(f"Audio saved to {self.file_name}.")

    def start_recording(self):
        """Începe înregistrarea audio."""
        if not self.find_blackhole_device():
            raise Exception("BlackHole loopback device not found. Make sure it is correctly installed.")

        stream = self.audio.open(format=pyaudio.paInt16,
                                 channels=self.channels,
                                 rate=self.sample_rate,
                                 input=True,
                                 input_device_index=self.input_device_index,
                                 frames_per_buffer=2048)
        self.is_recording = True
        log_info("Audio recording started.")
        for _ in range(0, int(self.sample_rate / 2048 * self.duration)):
            if not self.is_recording:
                break
            data = stream.read(2048)
            self.frames.append(data)

        stream.stop_stream()
        stream.close()
        self.audio.terminate()

        self.save_audio()
        log_info("Audio recording stopped.")



    def stop_recording(self):
        """Oprește înregistrarea audio."""
        self.is_recording = False


# Înregistrare video
class VideoRecorder:
    def __init__(self, duration=60, file_name="video.mp4", fps=20.0):
        self.duration = duration
        self.file_name = file_name
        self.fps = fps
        self.frames = []
        self.is_recording = False
        self.start_time = None

    def start_recording(self):
        """Începe înregistrarea video."""
        self.is_recording = True
        self.start_time = time.time()
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primul monitor
            log_info("Video recording started.")
            while self.is_recording and (time.time() - self.start_time < self.duration):
                img = sct.grab(monitor)
                frame = np.array(img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                self.frames.append(frame)

        self.save_video()
        log_info("Video recording stopped.")

    def save_video(self):
        """Salvează cadrele capturate într-un fișier video."""
        if self.frames:
            height, width, _ = self.frames[0].shape
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec pentru MP4
            video_writer = cv2.VideoWriter(self.file_name, fourcc, self.fps, (width, height))
            for frame in self.frames:
                video_writer.write(frame)
            video_writer.release()
        log_info(f"Video saved to {self.file_name}.")

    def stop_recording(self):
        """Oprește înregistrarea video."""
        self.is_recording = False


# Coordonator pentru înregistrarea audio și video
class AVRecorder:
    def __init__(self, duration=60, audio_file="audio.wav", video_file="video.mp4",output_file="final_output.mp4"):
        self.audio_recorder = AudioRecorder(duration=duration, file_name=audio_file)
        self.video_recorder = VideoRecorder(duration=duration, file_name=video_file)
        self.audio_file = audio_file
        self.video_file = video_file
        self.output_file = output_file
        self.audio_thread = None
        self.video_thread = None
        self.is_stopped=False

    def start(self):
        """Pornește înregistrarea audio și video pe thread-uri separate."""
        log_info("Starting AVRecorder (audio + video).")
        self.audio_thread = threading.Thread(target=self.audio_recorder.start_recording)
        self.video_thread = threading.Thread(target=self.video_recorder.start_recording)
        self.audio_thread.start()
        self.video_thread.start()

    def merge_audio_video(self):
        """Combină fișierele audio și video într-un singur fișier."""
        log_info("Merging audio and video into final output.")
        try:
            video_input = ffmpeg.input(self.video_file)
            audio_input = ffmpeg.input(self.audio_file)

            ffmpeg.output(video_input, audio_input, self.output_file,
                          vcodec='libx264', acodec='aac', shortest=None).run(overwrite_output=True)

            log_info(f"Audio and video combined into {self.output_file}.")
        except Exception as e:
            log_error(f"Error merging audio and video: {e}")


    def stop(self):
        """Oprește înregistrarea audio și video."""
        if self.is_stopped:  # Verificăm dacă metoda a fost deja apelată
            log_info("AVRecorder is already stopped. Skipping redundant stop.")
            return

        log_info("Stopping AVRecorder (audio + video).")
        self.audio_recorder.stop_recording()
        self.video_recorder.stop_recording()

        if self.audio_thread:
            self.audio_thread.join()
        if self.video_thread:
            self.video_thread.join()

        self.is_stopped = True  # Marcăm AVRecorder ca oprit
        log_info("AVRecorder stopped (audio + video).")
        self.merge_audio_video()  # Apelăm funcția pentru combinarea fișierelor

    # def merge_audio_video(video_file, audio_file, output_file="output.mp4"):
    #     """Funcție pentru a combina fișierele audio și video într-un singur fișier."""
    #     video_input = ffmpeg.input(video_file)
    #     audio_input = ffmpeg.input(audio_file)
    #
    #     # Combină audio și video într-un singur fișier cu codecuri adecvate și sincronizează durata
    #     ffmpeg.output(video_input, audio_input, output_file, vcodec='libx264', acodec='aac', shortest=None).run(
    #         overwrite_output=True)
    #     print(f"Audio și video combinate în {output_file}")
    def cleanup(self):
        """Oprește înregistrarea audio și video dacă acestea rulează."""
        try:
            if not self.is_stopped:
                self.stop()  # Oprește înregistrarea doar dacă nu a fost deja oprită
        except Exception as e:
            log_error(f"Error during AVRecorder cleanup: {e}")




