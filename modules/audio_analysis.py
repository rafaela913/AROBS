from moviepy.editor import VideoFileClip  # Modul pentru manipularea fișierelor video și audio.
import numpy as np  # Bibliotecă pentru operații matematice și manipularea array-urilor.



class AudioAnalyzer:
    def __init__(self, video_path, output_file, segment_duration=0.1):
        """
        Inițializează analiza audio.
        :param video_path: Calea către fișierul video.
        :param output_file: Calea fișierului pentru salvarea analizei.
        :param segment_duration: Durata fiecărui segment analizat (în secunde).
        """
        self.video_path = video_path # Calea către fișierul video.
        self.output_file = output_file # Fișierul de ieșire pentru datele analizei.
        self.segment_duration = segment_duration # Durata fiecărui segment audio analizat.

    @staticmethod
    def calculate_db_level(audio_segment):
        """
        Calculează nivelul în dB al unui segment audio.
        :param audio_segment: Segment audio ca array numpy.
        :return: Nivelul dB al segmentului.
        """
        rms_value = np.sqrt(np.mean(audio_segment ** 2))  # Calculeaza valoarea RMS (Root Mean Square
        db_level = 20 * np.log10(rms_value + 1e-6)   # Conversie în dB (evităm log(0) prin adăugarea unui offset mic).
        return db_level # Returnează nivelul în dB.

    def analyze(self):
        """
        Analizează fișierul audio extras dintr-un videoclip și scrie nivelurile dB într-un fișier CSV.
        """
        video = VideoFileClip(self.video_path) # Deschide fișierul video.
        audio = video.audio # Extrage pista audio din videoclip.
        sample_rate = audio.fps # Obține rata de eșantionare audio (cadre pe secundă).
        duration = audio.duration # Obține durata totală a pistei audio (în secunde).

        with open(self.output_file, 'w') as file: # Deschide fișierul de ieșire pentru scriere.
            file.write("Timp(secunde),Nivel_dB\n")

            # Împarte durata totală în segmente de `segment_duration` secunde.
            num_segments = int(duration / self.segment_duration)

            for i in range(num_segments):
                t_start = i * self.segment_duration # Timpul de început al segmentului curent.
                t_end = t_start + self.segment_duration # Timpul de sfârșit al segmentului curent.

                # Extragem segmentul audio și îl convertim în numpy array
                audio_segment = audio.subclip(t_start, t_end).to_soundarray(fps=sample_rate)
                if audio_segment is not None:
                    # Face media canalelor stereo pentru a obține un semnal mono (dacă este cazul)
                    audio_mono = np.mean(audio_segment, axis=1)

                    # Calculăm nivelul dB și scriem în fișier
                    db_level = self.calculate_db_level(audio_mono)
                    file.write(f"{t_start:.2f},{db_level:.2f}\n")
                else:
                    file.write(f"{t_start:.2f},No audio data\n")

        print("Analiza audio finalizată și salvată în:", self.output_file)
