from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import dotenv_values
import os
import mtranslate as mt
import time
from selenium.common.exceptions import TimeoutException, NoSuchElementException

env_vars = dotenv_values(".env")
InputLanguage = env_vars.get("InputLanguage")

HtmlCode = '''<!DOCTYPE html>
<html lang="en">
<head>
    <title>Speech Recognition</title>
</head>
<body>
    <button id="start" onclick="startRecognition()">Start Recognition</button>
    <button id="end" onclick="stopRecognition()">Stop Recognition</button>
    <p id="output"></p>
    <p id="status" style="color:gray; font-size:12px;"></p>
    <script>
        const output = document.getElementById('output');
        const status = document.getElementById('status');
        let recognition;
        let shouldRestart = true; // Flag to control restart behavior
        
        function updateStatus(message) {
            status.textContent = new Date().toLocaleTimeString() + ': ' + message;
            console.log(message);
        }

        function startRecognition() {
            updateStatus("Starting recognition...");
            
            // Don't create a new recognition object if one exists
            if (!recognition) {
                try {
                    recognition = new webkitSpeechRecognition() || new SpeechRecognition();
                    recognition.lang = '';
                    recognition.continuous = true;
                    
                    recognition.onstart = function() {
                        updateStatus("Recognition started successfully");
                        shouldRestart = true;
                    };
                    
                    recognition.onresult = function(event) {
                        const transcript = event.results[event.results.length - 1][0].transcript;
                        output.textContent += transcript;
                        updateStatus("Speech detected: '" + transcript + "'");
                    };
                    
                    recognition.onend = function() {
                        updateStatus("Recognition ended. ShouldRestart=" + shouldRestart);
                        if (shouldRestart) {
                            try {
                                recognition.start();
                                updateStatus("Recognition restarted");
                            } catch (e) {
                                updateStatus("Error restarting: " + e.message);
                                // Wait a moment and try again
                                setTimeout(() => {
                                    try {
                                        recognition.start();
                                        updateStatus("Delayed restart successful");
                                    } catch (de) {
                                        updateStatus("Delayed restart failed: " + de.message);
                                    }
                                }, 300);
                            }
                        }
                    };
                    
                    recognition.onerror = function(event) {
                        updateStatus("Recognition error: " + event.error);
                    };
                } catch (e) {
                    updateStatus("Error creating recognition: " + e.message);
                    return;
                }
            } else {
                updateStatus("Recognition object already exists");
            }
            
            try {
                recognition.start();
                updateStatus("Start method called");
            } catch (e) {
                updateStatus("Error starting recognition: " + e.message);
                // Try recreating the recognition object
                recognition = null;
                setTimeout(startRecognition, 500);
            }
        }

        function stopRecognition() {
            updateStatus("Stopping recognition...");
            shouldRestart = false;
            
            if (recognition) {
                try {
                    recognition.stop();
                    updateStatus("Stop method called");
                } catch (e) {
                    updateStatus("Error stopping recognition: " + e.message);
                }
            } else {
                updateStatus("No recognition object to stop");
            }
            
            output.innerHTML = "";
        }
    </script>
</body>
</html>'''

HtmlCode = str(HtmlCode).replace("recognition.lang = '';", f"recognition.lang = '{InputLanguage}';")

os.makedirs("Data", exist_ok=True)
with open(r"Data\Voice.html", "w", encoding="utf-8") as f:
    f.write(HtmlCode)
current_dir = os.getcwd()
Link = f"{current_dir}/Data/Voice.html"

# Configure Chrome options with more stable settings
chrome_options = Options()
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"
chrome_options.add_argument(f'user-agent={user_agent}')
chrome_options.add_argument("--use-fake-ui-for-media-stream")
chrome_options.add_argument("--use-fake-device-for-media-stream")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
chrome_options.add_argument("--allow-running-insecure-content")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--no-sandbox")
# Add potentially stabilizing options
chrome_options.add_argument("--disable-features=NetworkService,NetworkServiceInProcess")
chrome_options.add_argument("--disable-extensions") 
chrome_options.add_argument("--disable-background-networking")
chrome_options.add_argument("--disable-sync")
chrome_options.add_argument("--headless=new")
# Add more options to address chunked data pipe error
chrome_options.add_argument("--disable-background-timer-throttling")
chrome_options.add_argument("--disable-breakpad")
chrome_options.add_argument("--disable-component-extensions-with-background-pages")
chrome_options.add_argument("--disable-client-side-phishing-detection")
chrome_options.add_argument("--blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4")
chrome_options.add_argument("--disable-ipc-flooding-protection")
chrome_options.add_argument("--disable-renderer-backgrounding")
chrome_options.add_argument("--disable-smooth-scrolling")
chrome_options.add_argument("--disable-backgrounding-occluded-windows")
chrome_options.add_argument("--disable-hang-monitor")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
# For chunked_data_pipe error specifically
chrome_options.add_experimental_option("prefs", {
    "profile.default_content_setting_values.media_stream_mic": 1,
    "profile.default_content_setting_values.media_stream_camera": 1,
    "profile.content_settings.exceptions.clipboard": {'*': {'setting': 1}},
})
chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources to load

# Global driver state
driver = None
VOICE_PAGE_READY = False # Flag to track if Voice.html is loaded and ready
MAX_WAIT_TIME = 3 # Reduce max wait time for elements (was 5)
POST_DETECTION_WAIT = 0.5 # Reduce wait after detecting text (was 0.75)
RECOGNITION_ACTIVE = False # Flag to track if recognition is active

TempDirPath = os.path.join(current_dir, "Frontend", "Files")

def GetMicrophoneStatus():
    """Retrieve the current microphone status from Mic.data."""
    try:
        mic_file_path = os.path.join(TempDirPath, "Mic.data")
        with open(mic_file_path, "r", encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        return "False"  # Default to mic off if file is missing
    except Exception as e:
        print(f"[Error] Failed to read microphone status: {e}")
        return "False"

def initialize_driver(attempt_load=True):
    """
    Initialize the Chrome WebDriver with optimized settings
    :param attempt_load: Whether to attempt loading the voice page
    :return: True if initialization successful, False otherwise
    """
    global driver, VOICE_PAGE_READY
    
    print("[Driver] Initializing Chrome WebDriver...")
    
    try:
        # Close existing driver if it exists
        if driver is not None:
            try:
                driver.quit()
                print("[Driver] Closed existing WebDriver instance")
            except Exception as e:
                print(f"[Driver] Error closing existing WebDriver: {e}")
            driver = None
        
        # Set up Chrome options with optimized settings
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use the new headless implementation
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-browser-side-navigation")
        chrome_options.add_argument("--disable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--window-size=1920,1080")
        # chrome_options.add_argument("--remote-debugging-port=9222")  # Commented out as it might conflict
        chrome_options.add_argument("--log-level=3")  # Reduce logging
        
        # Additional arguments to prevent network-related errors
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--ignore-ssl-errors")
        chrome_options.add_argument("--ignore-certificate-errors-spki-list")
        
        # Experimental options to prevent chunked data pipe errors
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.media_stream_mic": 1,
            "profile.default_content_setting_values.media_stream_camera": 1,
            "profile.default_content_setting_values.geolocation": 1,
            "profile.default_content_setting_values.notifications": 1,
            "profile.content_settings.exceptions.clipboard": {'*': {'setting': 1}},
            "profile.managed_default_content_settings.images": 2,
            "network.cookie.cookieBehavior": 0
        })
        
        chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources to load
        
        try:
            service = Service(ChromeDriverManager().install())
            print("[Driver] Starting Chrome with optimized settings...")
            
            # Initialize the driver with timeout
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)  # 30 second timeout for page loads
            
            # Only attempt to load the voice page if requested
            if attempt_load:
                # Load the voice recognition page with retry mechanism
                max_load_attempts = 2
                for load_attempt in range(max_load_attempts):
                    try:
                        print(f"[Driver] Loading voice recognition page (attempt {load_attempt+1}/{max_load_attempts}): {Link}")
                        driver.get(Link)
                        
                        # Check if page loaded successfully with timeout
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "start"))
                        )
                        
                        VOICE_PAGE_READY = True
                        print("[Driver] Voice recognition page loaded successfully")
                        break  # Exit retry loop on success
                    except TimeoutException:
                        print(f"[Driver] Timeout loading voice page (attempt {load_attempt+1})")
                        if load_attempt == max_load_attempts - 1:  # Last attempt
                            raise  # Re-raise the exception to be caught by outer try/except
                    except Exception as page_e:
                        print(f"[Driver] Error loading voice page (attempt {load_attempt+1}): {page_e}")
                        if load_attempt == max_load_attempts - 1:  # Last attempt
                            raise  # Re-raise the exception to be caught by outer try/except
                        time.sleep(1)  # Wait before retry
            else:
                print("[Driver] Driver initialized but skipping page load as requested")
            
            return True
        
        except Exception as e:
            print(f"[Driver] Initialization error: {e}")
            # Clean up failed driver instance
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
            
            VOICE_PAGE_READY = False
            return False

    except Exception as e:
        print(f"[Driver] Initialization error: {e}")
        # Clean up failed driver instance
        if driver:
            try:
                driver.quit()
            except:
                pass
            driver = None
        
        VOICE_PAGE_READY = False
        return False

# Initialize driver and attempt initial page load
initialize_driver()

def SetAssistantStatus(Status):
    status_file_path = os.path.join(TempDirPath, "Status.data")
    with open(status_file_path, "w", encoding='utf-8') as file:
        file.write(Status)

def QueryModifier(Query):
    new_query = Query.lower().strip()
    query_words = new_query.split()
    question_words = ["how", "what", "who", "where", "when", "why", "which", "whose", "whom", "can you", "what's", "where's", "how's", "can you"]
    
    if any(word + " " in new_query for word in question_words):
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "?"
        else:
            new_query += "?"
    else:
        if query_words[-1][-1] in ['.', '?', '!']:
            new_query = new_query[:-1] + "."
        else:
            new_query += "."
    return new_query.capitalize()

def UniversalTranslator(Text):
    english_translation = mt.translate(Text, "en", "auto")
    return english_translation.capitalize()

def SpeechRecognition(textbox=None):
    """
    Main speech recognition function
    :param textbox: Optional textbox to update with status
    :return: The recognized text or None on failure
    """
    global driver, RECOGNITION_ACTIVE, VOICE_PAGE_READY

    # Check microphone status before proceeding
    if GetMicrophoneStatus() != "True":
        print("[Speech] Microphone is off. Aborting recognition.")
        # Make sure to stop any existing recognition
        if driver is not None and VOICE_PAGE_READY:
            try:
                driver.execute_script("stopRecognition()")
                print("[Speech] Stopped any existing recognition due to mic off.")
            except Exception as e:
                print(f"[Speech] Error stopping recognition: {e}")
        return None

    print("[Speech] Starting speech recognition - mic status is True")
    
    # If driver is not ready, initialize it
    if driver is None or not VOICE_PAGE_READY:
        print("[Speech] Driver not ready. Initializing...")
        if textbox:
            textbox.config(text="Initializing speech recognition...")
        
        # Try to initialize up to 3 times
        for attempt in range(3):
            print(f"[Speech] Driver initialization attempt {attempt+1}/3")
            if initialize_driver():
                print("[Speech] Driver initialized successfully")
                break
            else:
                print(f"[Speech] Driver initialization failed (attempt {attempt+1}/3)")
                time.sleep(2)  # Wait before retry
                if attempt == 2:  # Last attempt
                    if textbox:
                        textbox.config(text="Failed to initialize speech recognition.")
                    print("[Speech] All driver initialization attempts failed")
                    return None

    # Ensure we're not already running a recognition session
    if RECOGNITION_ACTIVE:
        print("[Speech] Recognition already active, resetting...")
        try:
            driver.execute_script("stopRecognition()")
            time.sleep(0.5)  # Give it a moment to reset
            RECOGNITION_ACTIVE = False
        except Exception as e:
            print(f"[Speech] Error resetting active recognition: {e}")
            # Try reloading the page
            try:
                VOICE_PAGE_READY = False
                driver.get(Link)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, "start"))
                )
                VOICE_PAGE_READY = True
                print("[Speech] Reloaded page after recognition reset error")
            except Exception as reload_e:
                print(f"[Speech] Error reloading page: {reload_e}")
                return None
    
    try:
        RECOGNITION_ACTIVE = True
        print("[Speech] Starting recognition...")
        
        if textbox:
            textbox.config(text="Listening...")
        
        # Make sure page is loaded and ready
        try:
            # Refresh recognition page if needed (only once)
            if not VOICE_PAGE_READY:
                print("[Speech] Voice page not ready, reloading...")
                try:
                    driver.get(Link)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "start"))
                    )
                    VOICE_PAGE_READY = True
                except Exception as page_load_error:
                    print(f"[Speech] Error reloading voice page: {page_load_error}")
                    # Try to reinitialize driver without loading page first
                    if initialize_driver(attempt_load=False):
                        # Then explicitly try to load the page
                        driver.get(Link)
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.ID, "start"))
                        )
                        VOICE_PAGE_READY = True
                    else:
                        raise Exception("Failed to reinitialize driver")
            
            # Use executeScript to start recognition (more reliable than clicking)
            print("[Speech] Executing startRecognition() JavaScript function")
            driver.execute_script("startRecognition()")
            
            # Wait a moment to confirm recognition started
            time.sleep(0.5)
            
            # Wait for recognition to complete
            recognition_start_time = time.time()
            max_wait_time = 30  # Maximum time to wait for recognition (seconds)
            check_interval = 0.2  # How often to check for results
            
            while time.time() - recognition_start_time < max_wait_time:
                # Check mic status inside the loop
                if GetMicrophoneStatus() != "True":
                    print("[Speech] Mic turned off during loop. Stopping recognition.")
                    try:
                        # Use JavaScript directly instead of finding elements
                        driver.execute_script("stopRecognition()")
                        print("[Speech] Stopped recognition via JS from loop.")
                    except Exception as stop_err:
                        print(f"[Speech] Error stopping recognition from loop: {stop_err}")
                    RECOGNITION_ACTIVE = False
                    return None
                
                try:
                    # Check for status updates
                    try:
                        status_text = driver.find_element(By.ID, "status").text
                        if status_text and "Error" in status_text:
                            print(f"[Speech] Status error: {status_text}")
                    except NoSuchElementException:
                        pass  # Status element might not be available
                    
                    # Check for recognized text
                    text_element = driver.find_element(By.ID, "output")
                    recognized_text = text_element.text.strip()
                    
                    if recognized_text:
                        print(f"[Speech] Text recognized: {recognized_text}")
                        if textbox:
                            textbox.config(text="Processing...")
                        
                        # Text found - wait a moment for completion
                        time.sleep(POST_DETECTION_WAIT)
                        
                        # Get the final text
                        final_text = driver.find_element(By.ID, "output").text.strip()
                        print(f"[Speech] Final recognized text: {final_text}")
                        
                        # Reset UI by explicitly calling stopRecognition()
                        try:
                            driver.execute_script("stopRecognition()")
                            print("[Speech] Recognition stopped after text detected")
                        except Exception as reset_error:
                            print(f"[Speech] Error stopping recognition: {reset_error}")
                        
                        RECOGNITION_ACTIVE = False
                        # ---> IMPORTANT: Return the text regardless of current mic status <---
                        # Once we have text, we always return it even if mic got turned off
                        return final_text
                except Exception as check_error:
                    print(f"[Speech] Error checking recognition status: {check_error}")
                
                time.sleep(check_interval)
            
            print("[Speech] Recognition timed out")
            if textbox:
                textbox.config(text="Speech recognition timed out.")
        
        except Exception as rec_error:
            print(f"[Speech] Error during recognition: {rec_error}")
            # Mark page as not ready so we'll reload it next time
            VOICE_PAGE_READY = False
            
            # Try to recover for next attempt
            try:
                driver.refresh()
                time.sleep(1)
            except:
                pass
                
    except Exception as e:
        print(f"[Speech] Recognition error: {e}")
    
    finally:
        # Always make sure to reset the recognition active flag
        RECOGNITION_ACTIVE = False
        if textbox:
            textbox.config(text="Ready")
    
    return None

def voice(timeout=5, wait_for_audio=0.1, max_retries=3, current_retry=0):
    """
    Capture voice input and convert to text
    :param timeout: Maximum recording time in seconds
    :param wait_for_audio: Time to wait for audio detection
    :param max_retries: Maximum number of retry attempts
    :param current_retry: Current retry attempt number
    :return: Transcribed text or None if failed
    """
    global driver, VOICE_PAGE_READY
    
    # Check if microphone is enabled
    if GetMicrophoneStatus() != "True":
        print("[Voice] Microphone is off. Aborting voice capture.")
        return None
    
    # Check if we've exceeded max retries
    if current_retry > max_retries:
        print(f"[Voice] Exceeded maximum retries ({max_retries}). Giving up.")
        return None
    
    try:
        print(f"[Voice] Starting voice recognition (attempt {current_retry+1}/{max_retries+1})...")
        
        # Ensure driver is initialized
        if not VOICE_PAGE_READY or driver is None:
            print("[Voice] WebDriver not ready. Initializing...")
            if not initialize_driver():
                print("[Voice] Failed to initialize driver. Retrying...")
                time.sleep(1)  # Wait before retry
                return voice(timeout, wait_for_audio, max_retries, current_retry + 1)
        
        try:
            # Use direct JavaScript execution instead of finding elements
            print("[Voice] Starting recognition via JavaScript...")
            driver.execute_script("startRecognition()")
            print("[Voice] Recording started...")
            
            # Wait for the specified timeout
            time.sleep(timeout)
            
            # Stop the recognition
            driver.execute_script("stopRecognition()")
            print("[Voice] Recording stopped.")
            
            # Wait for transcription to appear
            time.sleep(POST_DETECTION_WAIT)
            
            try:
                # Get the transcription from the output element
                transcript_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "output"))
                )
                transcript = transcript_element.text.strip()
                
                if transcript:
                    print(f"[Voice] Transcription successful: '{transcript}'")
                    return transcript
                else:
                    print("[Voice] Empty transcription received.")
                    # Try the status element for diagnostic info
                    try:
                        status_text = driver.find_element(By.ID, "status").text
                        print(f"[Voice] Status info: {status_text}")
                    except:
                        pass
                    return None
                    
            except Exception as e:
                print(f"[Voice] Error retrieving transcription: {e}")
                # If we encounter an error during transcription retrieval,
                # retry with a fresh driver instance
                initialize_driver()
                return voice(timeout, wait_for_audio, max_retries, current_retry + 1)
                
        except Exception as e:
            error_msg = str(e)
            print(f"[Voice] Error during recording: {e}")
            
            # Check for specific browser errors
            if "chunked_data_pipe" in error_msg or "NetworkService" in error_msg:
                print("[Voice] Detected browser error. Reinitializing driver...")
                try:
                    driver.quit()
                except:
                    pass
                driver = None
                VOICE_PAGE_READY = False
                time.sleep(2)  # Wait a bit longer before retry
                # Reinitialize driver and retry
                initialize_driver()
                return voice(timeout, wait_for_audio, max_retries, current_retry + 1)
            else:
                # For other errors, just retry
                return voice(timeout, wait_for_audio, max_retries, current_retry + 1)
    
    except Exception as e:
        print(f"[Voice] Unexpected error: {e}")
        # Generic error handling - reinitialize and retry
        try:
            driver.quit()
        except:
            pass
        driver = None
        VOICE_PAGE_READY = False
        time.sleep(1)
        return voice(timeout, wait_for_audio, max_retries, current_retry + 1)

def read_transcript():
    """
    Read the transcription result from the webpage
    """
    global driver, VOICE_PAGE_READY
    
    try:
        if driver is None or not VOICE_PAGE_READY:
            print("[ReadTranscript] Driver not initialized or page not ready.")
            return ""
            
        # Wait for transcription to appear with explicit wait
        try:
            transcript_element = WebDriverWait(driver, MAX_WAIT_TIME).until(
                EC.presence_of_element_located((By.ID, "output"))
            )
            # Get transcript text
            transcript = transcript_element.text.strip()
            
            # Clear the transcript element for future use
            try:
                driver.execute_script("document.getElementById('output').innerText = '';")
            except Exception as clear_e:
                print(f"[ReadTranscript] Warning: Could not clear transcript: {clear_e}")
            
            return transcript
        except TimeoutException:
            print("[ReadTranscript] Timeout waiting for transcript element.")
            return ""
        except Exception as e:
            print(f"[ReadTranscript] Error reading transcript: {e}")
            if "chunked_data_pipe" in str(e).lower():
                print("[ReadTranscript] Detected chunked_data_pipe error. Reinitializing driver...")
                initialize_driver()
            return ""
            
    except Exception as e:
        print(f"[ReadTranscript] Unexpected error: {e}")
        return ""

if __name__ == "__main__":
    while True:
        Text = SpeechRecognition()
        print(Text)