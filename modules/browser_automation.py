import threading # Modul pentru a lucra cu thread-uri.
import time # Modul pentru operațiuni legate de timp (ex. pauze).
from selenium import webdriver # Selenium pentru automatizarea browserului.
from selenium.webdriver.common.by import By # Folosit pentru localizarea elementelor în DOM.
from selenium.webdriver.common.keys import Keys # Pentru interacțiuni cu tastatura, cum ar fi ENTER.
from selenium.webdriver.support.ui import WebDriverWait # Așteptare explicită până când un element devine disponibil.
from selenium.webdriver.support import expected_conditions as EC # Condiții pentru așteptări (ex. element clickabil).
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from modules.logger import log_info, log_error

class YouTubeNavigator:
    def __init__(self):
        self.driver = None # Driverul Selenium (Chrome în acest caz).
        self.video_ready_event = threading.Event()  # Eveniment pentru sincronizare
        self.lock = threading.Lock() # Lock pentru a evita conflicte între thread-uri.
        self.popup_monitor_thread = None # Thread pentru monitorizarea pop-up-urilor.
        self.monitor_popupss=True # Variabilă pentru a controla thread-ul de monitorizare.

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
            # Așteaptă până când apare butonul pentru acceptarea cookie-urilor.
            cookies_popup = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[.//span[text()='Accept all']]"))
            )
            # Scrolează pentru a face butonul vizibil și apoi dă click.
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
        while self.monitor_popupss:  # Rulează cât timp monitorizarea este activă.
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
        self.monitor_popupss = False # Dezactivează monitorizarea.
        if self.popup_monitor_thread and self.popup_monitor_thread.is_alive(): # Verifică dacă thread-ul rulează.
            self.popup_monitor_thread.join() # Așteaptă finalizarea thread-ului.
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
            self.driver.get("https://www.youtube.com") # Deschide YouTube în browser.
            self.wait_for_page_load()  # Așteaptă încărcarea completă a paginii.
            log_info("Navigated to YouTube.")
            self.handle_popups() # Gestionează eventualele pop-up-uri.
            time.sleep(1) # Pauză scurtă pentru stabilizare.
        except Exception as e:
            log_error(f"Failed to navigate to YouTube: {e}")



    def search_and_play_video(self,query="video test",duration=15):
        """Caută și redă un videoclip pe YouTube."""
        try:
            # Resetează evenimentul la început
            self.video_ready_event.clear()
            # Așteaptă și găsește bara de căutare.
            search_box = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.NAME, "search_query"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);",
                                       search_box)  # Se asigura că bara este vizibilă
            search_box.click() # Dă click pe bara de căutare.
            time.sleep(0.5)
            search_box.clear() # Șterge textul existent.
            time.sleep(0.5)
            search_box.send_keys(query) # Introduc textul căutării.
            search_box.send_keys(Keys.RETURN) # Apasă Enter.
            log_info(f"Searched for: {query}")

            # Găsește și dă click pe primul videoclip.
            video = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[@id='video-title']"))
            )
            video.click()
            log_info("Video clicked and playing.")

            # Așteaptă până când videoclipul începe să ruleze.
            WebDriverWait(self.driver, 5).until(
                lambda d: "Pause" in d.find_element(By.CLASS_NAME, "ytp-play-button").get_attribute("title")
            )
            log_info("Video is playing.")
            self.video_ready_event.set()  # Semnalizare că videoclipul rulează

            # Rulează monitorizarea pop-up-urilor într-un thread separat
            self.popup_monitor_thread = threading.Thread(target=self.monitor_popups, daemon=True)
            self.popup_monitor_thread.start()
            time.sleep(duration) # Rulează videoclipul pentru durata specificată.


        except (TimeoutException, NoSuchElementException, ElementNotInteractableException) as e:
            log_error(f"Error searching or playing video: {e}")
            self.video_ready_event.set()  # Semnalizare chiar și în caz de eroare

    def stop_video(self):
        """Oprește redarea videoclipului."""
        try:
            play_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "ytp-play-button"))
            )
            play_button.click() # Dă click pe butonul de oprire/redare.
            log_info("Video playback stopped.")
        except Exception as e:
            log_error(f"Error stopping video playback: {e}")

    def close_browser(self):
        """Curăță procesele active și închide browserul."""
        self.stop_popup_monitor() # Oprește monitorizarea pop-up-urilor.
        if self.driver:
            self.driver.quit() # Închide browserul.
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


