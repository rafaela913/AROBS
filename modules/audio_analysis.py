from moviepy.editor import VideoFileClip
import numpy as np


class AudioAnalyzer:
    def __init__(self, video_path, output_file, segment_duration=0.1):
        """
        Inițializează analiza audio.
        :param video_path: Calea către fișierul video.
        :param output_file: Calea fișierului pentru salvarea analizei.
        :param segment_duration: Durata fiecărui segment analizat (în secunde).
        """
        self.video_path = video_path
        self.output_file = output_file
        self.segment_duration = segment_duration

    @staticmethod
    def calculate_db_level(audio_segment):
        """
        Calculează nivelul în dB al unui segment audio.
        :param audio_segment: Segment audio ca array numpy.
        :return: Nivelul dB al segmentului.
        """
        rms_value = np.sqrt(np.mean(audio_segment ** 2))  # Calculăm valoarea RMS
        db_level = 20 * np.log10(rms_value + 1e-6)  # Conversie în dB (evităm log(0))
        return db_level

    def analyze(self):
        """
        Analizează fișierul audio extras dintr-un videoclip și scrie nivelurile dB într-un fișier CSV.
        """
        video = VideoFileClip(self.video_path)
        audio = video.audio
        sample_rate = audio.fps
        duration = audio.duration

        with open(self.output_file, 'w') as file:
            file.write("Timp(secunde),Nivel_dB\n")

            # Segmentare audio în intervale de segment_duration
            num_segments = int(duration / self.segment_duration)

            for i in range(num_segments):
                t_start = i * self.segment_duration
                t_end = t_start + self.segment_duration

                # Extragem segmentul audio și îl convertim în numpy array
                audio_segment = audio.subclip(t_start, t_end).to_soundarray(fps=sample_rate)
                if audio_segment is not None:
                    # Media canalelor stereo (dacă există)
                    audio_mono = np.mean(audio_segment, axis=1)

                    # Calculăm nivelul dB și scriem în fișier
                    db_level = self.calculate_db_level(audio_mono)
                    file.write(f"{t_start:.2f},{db_level:.2f}\n")
                else:
                    file.write(f"{t_start:.2f},No audio data\n")

        print("Analiza audio finalizată și salvată în:", self.output_file)
