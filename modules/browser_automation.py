import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from modules.logger import log_info, log_error

class YouTubeNavigator:
    def __init__(self):
        self.driver = None
        self.video_ready_event = threading.Event()  # Eveniment pentru sincronizare
        self.lock = threading.Lock()
        self.popup_monitor_thread = None
        self.monitor_popupss=True

    def initialize_driver(self):
        """Inițializează WebDriver-ul Chrome."""
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        self.driver = webdriver.Chrome(options=options)
        log_info("WebDriver initialized.")

    def handle_popups(self):
        """Gestionează pop-up-urile de pe YouTube."""
        try:
            cookies_popup = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Accept all']]"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", cookies_popup)
            cookies_popup.click()
            log_info("Cookies popup accepted.")
        except TimeoutException:
            log_info("No cookie pop-up found.")
        except Exception as e:
            log_info(f"Error while accepting cookies: {e}")

    def monitor_popups(self):
        """Monitorizează și închide pop-up-uri care apar în timpul redării videoclipului."""
        log_info("Încep monitorizarea pop-up-urilor.")
        while self.monitor_popupss:
            time.sleep(1)  # Interval de 1 secundă între verificări
            with self.lock:  # Evităm conflictele cu alte thread-uri
                try:
                    # Verifică existența butonului "Dismiss" (pentru YouTube Premium)
                    dismiss_button = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="dismiss-button"]/yt-button-shape/button'))
                    )
                    dismiss_button.click()
                    log_info("Pop-up YouTube Premium (Dismiss) închis.")
                except TimeoutException:
                    # Dacă nu există pop-up, continuăm
                    pass
                except Exception as e:
                    log_error(f"Eroare la monitorizarea pop-up-urilor: {e}")

    def stop_popup_monitor(self):
        """Oprește thread-ul pentru monitorizarea pop-up-urilor."""
        self.monitor_popupss = False
        if self.popup_monitor_thread and self.popup_monitor_thread.is_alive():
            self.popup_monitor_thread.join()
            log_info("Popup monitor thread stopped.")

    def wait_for_page_load(self):
        """Așteaptă ca pagina să fie complet încărcată."""
        WebDriverWait(self.driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        log_info("Page fully loaded.")

    def navigate_to_youtube(self):
        """Navighează către YouTube."""
        try:
            self.driver.get("https://www.youtube.com")
            self.wait_for_page_load()  # Asigură-te că pagina este complet încărcată
            log_info("Navigated to YouTube.")
            self.handle_popups()
            time.sleep(1)
        except Exception as e:
            log_error(f"Failed to navigate to YouTube: {e}")



    def search_and_play_video(self,query="video test",duration=15):
        """Caută și redă un videoclip pe YouTube."""
        try:
            # Resetează evenimentul la început
            self.video_ready_event.clear()
            search_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "search_query"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);",
                                       search_box)  # Asigură-te că bara este vizibilă
            search_box.click()
            time.sleep(0.5)
            search_box.clear()
            time.sleep(0.5)
            search_box.send_keys(query)
            search_box.send_keys(Keys.RETURN)
            log_info(f"Searched for: {query}")

            video = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@id='video-title']"))
            )
            video.click()
            log_info("Video clicked and playing.")

            WebDriverWait(self.driver, 5).until(
                lambda d: "Pause" in d.find_element(By.CLASS_NAME, "ytp-play-button").get_attribute("title")
            )
            log_info("Video is playing.")
            self.video_ready_event.set()  # Semnalizare că videoclipul rulează

            # Rulează monitorizarea pop-up-urilor într-un thread separat
            self.popup_monitor_thread = threading.Thread(target=self.monitor_popups, daemon=True)
            self.popup_monitor_thread.start()
            time.sleep(duration)


        except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
            log_error(f"Error searching or playing video: {e}")
            self.video_ready_event.set()  # Semnalizare chiar și în caz de eroare

    def stop_video(self):
        """Oprește redarea videoclipului."""
        try:
            play_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "ytp-play-button"))
            )
            play_button.click()
            log_info("Video playback stopped.")
        except Exception as e:
            log_error(f"Error stopping video playback: {e}")

    def close_browser(self):
        """Curăță procesele active și închide browserul."""
        self.stop_popup_monitor()
        if self.driver:
            self.driver.quit()
            self.driver=None
            log_info("Browser closed.")

def youtube_navigation_task(navigator):
    """Task-ul care va rula în thread."""
    try:
        navigator.initialize_driver()
        navigator.navigate_to_youtube()
        navigator.search_and_play_video()
    except Exception as e:
        log_error(f"Error in YouTube navigation: {e}")
    finally:
        log_info("YouTube navigation task completed.")


