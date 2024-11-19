import threading
import time
import cv2 # OpenCV pentru procesarea imaginilor și salvarea videoclipurilor.
import numpy as np # Numpy pentru manipularea cadrelor video.
import pyaudio # Modul pentru înregistrarea și redarea audio.
import wave  # Modul pentru manipularea fișierelor audio în format WAV.
import mss # Modul pentru capturarea ecranului.
from modules.logger import log_info, log_error  # Logger propriu
import ffmpeg # Bibliotecă pentru procesarea audio și video.


# Înregistrare audio
class AudioRecorder:
    def __init__(self, duration=60, file_name="audio.wav"):
        # Configurări inițiale pentru înregistrare audio.
        self.sample_rate = 44100  # Rata de eșantionare (44.1 kHz).
        self.channels = 2 # Înregistrare stereo (2 canale).
        self.duration = duration # Durata înregistrării, în secunde.
        self.file_name = file_name # Numele fișierului unde se va salva audio.
        self.audio = pyaudio.PyAudio() # Inițializează modulul PyAudio.
        self.frames = [] # Cadrele audio capturate.
        self.is_recording = False # Flag pentru a indica dacă înregistrarea rulează.

    def find_blackhole_device(self):
        """Găsește dispozitivul BlackHole pentru înregistrare audio."""
        for i in range(self.audio.get_device_count()):  # Iterează prin toate dispozitivele audio disponibile.
            device_info = self.audio.get_device_info_by_index(i)
            if "BlackHole" in device_info['name']:  # Verifică dacă dispozitivul este BlackHole.
                self.input_device_index = i  # Setează indexul dispozitivului BlackHole.
                log_info(f"Found BlackHole device: {device_info['name']}")  # Logare: dispozitiv găsit.
                return True
        log_info("BlackHole loopback device not found.")  # Logare: dispozitivul nu a fost găsit.
        return False

    def save_audio(self):
        """Salvează înregistrarea audio într-un fișier WAV."""
        with wave.open(self.file_name, 'wb') as wf:  # Creează fișierul audio.
            wf.setnchannels(self.channels)  # Setează numărul de canale (stereo).
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))  # Setează dimensiunea eșantionului (16 biți).
            wf.setframerate(self.sample_rate)  # Setează rata de eșantionare.
            wf.writeframes(b''.join(self.frames))  # Scrie cadrele audio capturate în fișier.
        log_info(f"Audio saved to {self.file_name}.")  # Logare: audio salvat.

    def start_recording(self):
        """Începe înregistrarea audio."""
        if not self.find_blackhole_device(): # Verifică dacă dispozitivul BlackHole este disponibil.
            raise Exception("BlackHole loopback device not found. Make sure it is correctly installed.")

        stream = self.audio.open(format=pyaudio.paInt16,
                                 channels=self.channels,
                                 rate=self.sample_rate,
                                 input=True,
                                 input_device_index=self.input_device_index,
                                 frames_per_buffer=2048) # Configurare flux audio.
        self.is_recording = True
        log_info("Audio recording started.")
        for _ in range(0, int(self.sample_rate / 2048 * self.duration)): # Iterează pentru durata specificată.
            if not self.is_recording: # Dacă este oprită, oprește bucla.
                break
            data = stream.read(2048) # Citește datele audio din flux.
            self.frames.append(data) # Stochează datele audio.

        stream.stop_stream()  # Oprește fluxul.
        stream.close()  # Închide fluxul.
        self.audio.terminate()  # Închide PyAudio.

        self.save_audio() # Salvează audio în fișier.
        log_info("Audio recording stopped.")



    def stop_recording(self):
        """Oprește înregistrarea audio."""
        self.is_recording = False


# Înregistrare video
class VideoRecorder:
    def __init__(self, duration=60, file_name="video.mp4", fps=20.0):
        # Configurări inițiale pentru înregistrare video.
        self.duration = duration  # Durata înregistrării video, în secunde.
        self.file_name = file_name  # Numele fișierului video.
        self.fps = fps  # Cadre pe secundă.
        self.frames = []  # Cadrele video capturate.
        self.is_recording = False  # Flag pentru a indica dacă înregistrarea rulează.
        self.start_time = None  # Timpul de start al înregistrării.

    def start_recording(self):
        """Începe înregistrarea video."""
        self.is_recording = True
        self.start_time = time.time() # Înregistrează timpul de start.
        with mss.mss() as sct: # Creează obiect pentru capturarea ecranului.
            monitor = sct.monitors[1]  # Selectează primul monitor.
            log_info("Video recording started.")
            while self.is_recording and (time.time() - self.start_time < self.duration): # Rulează pentru durata specificată.
                img = sct.grab(monitor) # Capturează ecranul.
                frame = np.array(img) # Conversie la array NumPy.
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR) # Conversie la format RGB.
                self.frames.append(frame) # Adaugă cadrul în lista de cadre.

        self.save_video() # Salvează cadrele în fișier.
        log_info("Video recording stopped.")

    def save_video(self):
        """Salvează cadrele capturate într-un fișier video."""
        if self.frames: # Verifică dacă există cadre capturate.
            height, width, _ = self.frames[0].shape # Obține dimensiunile cadrelor.
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec pentru MP4
            video_writer = cv2.VideoWriter(self.file_name, fourcc, self.fps, (width, height)) # Inițializează scriitorul video.
            for frame in self.frames:
                video_writer.write(frame) # Scrie fiecare cadru în fișier.
            video_writer.release() # Închide scriitorul video.
        log_info(f"Video saved to {self.file_name}.")

    def stop_recording(self):
        """Oprește înregistrarea video."""
        self.is_recording = False


# Coordonator pentru înregistrarea audio și video
class AVRecorder:
    def __init__(self, duration=60, audio_file="audio.wav", video_file="video.mp4",output_file="final_output.mp4"):
        # Inițializează înregistrările audio și video.
        self.audio_recorder = AudioRecorder(duration=duration, file_name=audio_file)
        self.video_recorder = VideoRecorder(duration=duration, file_name=video_file)
        self.audio_file = audio_file
        self.video_file = video_file
        self.output_file = output_file
        self.audio_thread = None
        self.video_thread = None
        self.is_stopped=False # Flag pentru a indica dacă înregistrarea s-a oprit.

    def start(self):
        """Pornește înregistrarea audio și video pe thread-uri separate."""
        log_info("Starting AVRecorder (audio + video).")
        self.audio_thread = threading.Thread(target=self.audio_recorder.start_recording) # Creează thread audio.
        self.video_thread = threading.Thread(target=self.video_recorder.start_recording) # Creează thread video.
        self.audio_thread.start()
        self.video_thread.start()

    def merge_audio_video(self):
        """Combină fișierele audio și video într-un singur fișier."""
        log_info("Merging audio and video into final output.")
        try:
            video_input = ffmpeg.input(self.video_file) # Fișier video.
            audio_input = ffmpeg.input(self.audio_file) # Fișier audio.

            ffmpeg.output(video_input, audio_input, self.output_file,
                          vcodec='libx264', acodec='aac', shortest=None).run(overwrite_output=True) # Combină fișierele.

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
            self.audio_thread.join() # Așteaptă finalizarea thread-ului audio.
        if self.video_thread:
            self.video_thread.join() # Așteaptă finalizarea thread-ului video.

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




