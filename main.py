# Funcția principală
import threading
import time
import socket
from modules.audio_analysis import AudioAnalyzer
from modules.browser_automation import YouTubeNavigator
from modules.logger import log_info, log_error
from modules.screen_recorder import AVRecorder

# Funcții pentru detectarea și gestionarea conexiunii la internet
def check_internet_connection(timeout=5):
    """
    Verifică dacă există conexiune la internet.
    :param timeout: Timpul de așteptare pentru verificare.
    :return: True dacă conexiunea există, False altfel.
    """
    try:
        socket.create_connection(("www.youtube.com", 443), timeout=timeout)
        return True
    except OSError:
        return False


def wait_for_connection(retry_interval=10, max_retries=5):
    """
    Așteaptă până când conexiunea la internet revine.
    :param retry_interval: Intervalul de timp între verificări (în secunde).
    :param max_retries: Numărul maxim de încercări.
    :return: True dacă conexiunea revine, False altfel.
    """
    retries = 0
    while retries < max_retries:
        if check_internet_connection():
            log_info("Internet connection established.")
            return True
        else:
            log_error(f"No internet connection. Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)
            retries += 1

    log_error("Max retries reached. Internet connection not available.")
    return False

def main():
    duration = 15  # Durata totală a înregistrării
    audio_file = "output_audio.wav"
    video_file = "screen_recording.mp4"
    final_file = "final_output.mp4"
    analysis_output_file = "nivel_sunet_dB.txt"

    # Inițializăm obiectele
    youtube_navigator = YouTubeNavigator()
    av_recorder = AVRecorder(duration=duration, audio_file=audio_file, video_file=video_file, output_file=final_file)

    try:
        # Verificăm conexiunea la internet
        if not check_internet_connection():
            log_error("No internet connection detected. Waiting for reconnection...")
            if not wait_for_connection():
                raise Exception("Unable to connect to the internet. Exiting.")

        # Pornim navigarea pe YouTube într-un thread separat
        def youtube_task():
            youtube_navigator.initialize_driver()
            youtube_navigator.navigate_to_youtube()
            youtube_navigator.search_and_play_video("test video")

        youtube_thread = threading.Thread(target=youtube_task)
        youtube_thread.start()

        # Așteptăm ca videoclipul să înceapă redarea
        log_info("Waiting for video to start...")
        youtube_navigator.video_ready_event.wait(timeout=30)

        if not youtube_navigator.video_ready_event.is_set():
            raise TimeoutError("Video did not start playing in time.")

        log_info("Video started. Starting recording...")

        # În paralel, pornim înregistrarea audio și video
        av_recorder.start()
        time.sleep(duration)

        # Așteptăm finalizarea redării video și a înregistrării
        youtube_thread.join()
        
        # Pornim merge-ul pe un thread separat
        def merge_task():
            av_recorder.stop()  # Aceasta include merge-ul audio-video

        merge_thread = threading.Thread(target=merge_task)
        merge_thread.start()

        youtube_navigator.close_browser()
        log_info("Browser closed after duration.")

        # Așteptăm finalizarea merge-ului
        merge_thread.join()

        log_info(f"Recording completed. Final output: {final_file}")

        analyzer = AudioAnalyzer(video_path=final_file, output_file=analysis_output_file)
        analyzer.analyze()

    except Exception as e:
        log_error(f"An error occurred: {e}")
    finally:
        # Curățăm procesele active
        try:
            av_recorder.cleanup()
        except Exception as e:
            log_error(f"Error during AVRecorder cleanup: {e}")
        try:
            youtube_navigator.close_browser()
        except Exception as e:
            log_error(f"Error during YouTubeNavigator cleanup: {e}")




if __name__ == "__main__":
    main()