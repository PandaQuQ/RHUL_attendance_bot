import os
import sys
import os
import sys
import logging
import math
import json
import threading
import time
import random
import shutil
import subprocess
import zoneinfo  # For Python 3.9 and above
import ntplib  # Used to check system time synchronization

# Create a logger
logger = logging.getLogger("attendance_bot")
logger.setLevel(logging.DEBUG)

def check_virtual_environment():
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        logger.info("Running inside a virtual environment.")
    else:
        logger.error("You are not running inside a Python virtual environment.")
        logger.error("Please create a Python virtual environment and activate it before running this script.")
        sys.exit(1)

def check_dependencies():
    missing_packages = []
    required_packages = []
    requirements_file = 'requirements.txt'
    if not os.path.exists(requirements_file):
        logger.error(f"Requirements file '{requirements_file}' not found.")
        logger.error(f"Please ensure the '{requirements_file}' file is in the same directory as the script.")
        sys.exit(1)
    with open(requirements_file, 'r') as f:
        required_packages = [line.strip() for line in f if line.strip()]
    try:
        installed_packages_output = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze']).decode()
    except subprocess.CalledProcessError as e:
        logger.error("Failed to get installed packages.")
        sys.exit(1)
    installed_packages = [pkg.lower().split('==')[0] for pkg in installed_packages_output.strip().split('\n') if pkg.strip()]
    for pkg in required_packages:
        pkg_name = pkg.lower().split('==')[0]
        if pkg_name not in installed_packages:
            missing_packages.append(pkg)
    if missing_packages:
        logger.error(f"Missing dependencies: {', '.join(missing_packages)}")
        logger.error("Please install the dependencies by running 'pip install -r requirements.txt'")
        sys.exit(1)
    else:
        logger.info("All dependencies are installed.")

def check_chrome_installed():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")  # Run in headless mode for testing
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.quit()
        logger.info("Chrome and ChromeDriver are installed and working.")
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        logger.error("Please ensure that Google Chrome is installed and accessible.")
        sys.exit(1)

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    check_virtual_environment()
    check_dependencies()
    check_chrome_installed()

    # First-run check: credentials and timetable
    credentials_path = os.path.join(script_dir, 'credentials.json')
    ics_folder = os.path.join(script_dir, 'ics')
    ics_file = os.path.join(ics_folder, 'student_timetable.ics')
    first_run = False
    # Check credentials
    creds_ok = False
    if os.path.exists(credentials_path):
        try:
            import json
            with open(credentials_path, 'r') as f:
                creds = json.load(f)
            if 'username' in creds and 'password' in creds and creds['username'] and creds['password']:
                creds_ok = True
        except Exception:
            creds_ok = False
    # Check timetable
    timetable_ok = os.path.exists(ics_file)
    if not creds_ok or not timetable_ok:
        first_run = True

    # Onboarding if first run
    if first_run:
        print('First run detected: running onboarding steps...')
        # Run auto_login.py for first-time login
        subprocess.run([sys.executable, os.path.join(script_dir, 'auto_login.py')])
        # Run fetch_ics.py to get timetable
        subprocess.run([sys.executable, os.path.join(script_dir, 'fetch_ics.py')])

    # Now proceed to import the rest of the modules
    import threading
    import time
    import random
    import shutil
    from datetime import datetime, timedelta, timezone
    from ics import Calendar
    from rich.console import Console
    from rich.panel import Panel
    from rich.live import Live
    from rich.table import Table
    from rich.align import Align
    from rich.text import Text
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    from pynput import keyboard
    from collections import deque
    import zoneinfo  # For Python 3.9 and above
    import ntplib  # Used to check system time synchronization
    from auto_login import renew_login
    # Reuse helpers but add custom MFA fallback below

    # Initialize Rich console
    console = Console()

    # Reconfigure logger to add file handler and buffer handler
    logger.handlers = []  # Remove previous handlers
    logger.setLevel(logging.DEBUG)
    
    # Create a file handler to log INFO and above messages with timestamps
    file_handler = logging.FileHandler('automation.log', encoding='utf-8', mode='a')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Create a fixed-size deque to store the latest five log messages
    log_buffer = deque(maxlen=5)
    log_buffer_lock = threading.Lock()
    
    # Custom BufferLogHandler to store logs in deque and format with Rich
    class BufferLogHandler(logging.Handler):
        def __init__(self, buffer, buffer_lock, console):
            super().__init__()
            self.buffer = buffer
            self.buffer_lock = buffer_lock
            self.console = console

        def emit(self, record):
            log_entry = self.format(record)
            with self.buffer_lock:
                # Add color to log levels
                if record.levelno == logging.INFO:
                    log_entry = f"[green]{log_entry}[/green]"
                elif record.levelno == logging.WARNING:
                    log_entry = f"[yellow]{log_entry}[/yellow]"
                elif record.levelno == logging.ERROR:
                    log_entry = f"[red]{log_entry}[/red]"
                elif record.levelno == logging.DEBUG:
                    log_entry = f"[blue]{log_entry}[/blue]"
                self.buffer.append(log_entry)

    # Configure BufferLogHandler to display message content without timestamps and levels
    buffer_handler = BufferLogHandler(log_buffer, log_buffer_lock, console)
    buffer_handler.setLevel(logging.DEBUG)
    buffer_formatter = logging.Formatter('%(message)s')
    buffer_handler.setFormatter(buffer_formatter)
    logger.addHandler(buffer_handler)
    
    # Initialize global variables
    global start_time, attendance_success_count, counter_lock, events_lock, exit_event
    start_time = datetime.now()
    attendance_success_count = 0
    
    # Locks for thread-safe updates
    counter_lock = threading.Lock()
    events_lock = threading.Lock()  # Lock for upcoming_events
    exit_event = threading.Event()  # Event to signal exit

    def verify_login(driver, expected_url, max_wait_minutes=30):
        initial_wait = 3
        periodic_wait = 10
        max_wait_seconds = max_wait_minutes * 60
        elapsed_time = 0

        time.sleep(initial_wait)
        current_url = driver.current_url

        if current_url == expected_url:
            logger.info("Already logged in.")
            return True
        else:
            logger.info("Need to login.")

        while current_url != expected_url and elapsed_time < max_wait_seconds:
            time.sleep(periodic_wait)
            elapsed_time += periodic_wait
            current_url = driver.current_url
            if current_url == expected_url:
                logger.info("Login detected.")
                return True
            else:
                logger.info("Waiting for login...")
        
        logger.error(f"Login not detected after {max_wait_minutes} minutes.")
        return False

    def initialize_webdriver(user_data_dir):
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={user_data_dir}")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        # Add more options if needed
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome WebDriver initialized successfully.")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}", exc_info=True)
            return None

    def click_button_if_visible(driver, button_ids):
        button_flag = False
        for button_id in button_ids:
            try:
                button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, button_id)))
                driver.execute_script("arguments[0].click();", button)
                logger.info(f"Clicked button: {button_id}")
                button_flag = True
                return True
            except Exception:
                pass
        if button_flag is False:
            logger.error("Error clicking buttons: Can't find any button", exc_info=True)
        logger.warning("No clickable button found.")
        return False

    def click_by_xpath_contains_text(driver, text, timeout=10):
        xpath = f"//*[self::button or self::a or self::div or self::span][contains(normalize-space(.), '{text}')]"
        try:
            elem = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].click();", elem)
            logger.info(f"Clicked element with text contains: {text}")
            return True
        except Exception:
            return False

    def click_with_retries(driver, candidates, attempts=6, delay=1.0):
        """Try multiple selectors, with normal then JS click, retrying for dynamic UI."""
        for attempt in range(1, attempts + 1):
            for by, sel, label in candidates:
                try:
                    elems = driver.find_elements(by, sel)
                    logger.info(f"[MFA click attempt {attempt}] selector={sel} label={label} found={len(elems)}")
                    for elem in elems:
                        if not elem.is_displayed() or not elem.is_enabled():
                            continue
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                        try:
                            elem.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", elem)
                        logger.info(f"[MFA click attempt {attempt}] clicked {label} via {sel}")
                        return True
                except Exception as e:
                    logger.debug(f"[MFA click attempt {attempt}] selector={sel} error={e}")
                    continue
            time.sleep(delay)
        logger.error("MFA click_with_retries exhausted without a click")
        return False

    def maybe_switch_to_login_iframe(driver):
        """If login fields are inside an iframe, switch into it."""
        try:
            driver.switch_to.default_content()
            frames = driver.find_elements(By.TAG_NAME, 'iframe')
            for frame in frames:
                try:
                    driver.switch_to.frame(frame)
                    if driver.find_elements(By.NAME, 'loginfmt') or driver.find_elements(By.ID, 'i0116'):
                        return True
                except Exception:
                    driver.switch_to.default_content()
            driver.switch_to.default_content()
        except Exception:
            driver.switch_to.default_content()
        return False

    def handle_kmsi(driver):
        """Tick 'Don't show this again' (KMSI) and confirm Yes/Next."""
        try:
            kmsi_checkbox = driver.find_element(By.ID, "KmsiCheckboxField")
            if kmsi_checkbox.is_displayed() and kmsi_checkbox.is_enabled() and not kmsi_checkbox.is_selected():
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", kmsi_checkbox)
                try:
                    kmsi_checkbox.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", kmsi_checkbox)
                logger.info("Ticked KMSI checkbox")
                time.sleep(0.3)
        except Exception:
            pass

        # Confirm buttons
        candidates = [
            (By.ID, 'idSIButton9', 'idSIButton9'),
            (By.CSS_SELECTOR, "input[type='submit'].button_primary", "button_primary submit"),
            (By.XPATH, "//input[@type='submit' and (contains(@value,'Yes') or contains(@value,'是') or contains(@value,'继续') or contains(@value,'Next') or contains(@value,'Sign in'))]", "submit value match"),
            (By.XPATH, "//button[contains(normalize-space(.), 'Yes') or contains(normalize-space(.), '是') or contains(normalize-space(.), '继续') or contains(normalize-space(.), 'Next') or contains(normalize-space(.), 'Sign in') or contains(normalize-space(.), 'Accept') or contains(normalize-space(.), '登录') or contains(normalize-space(.), '同意')]", "button text match"),
        ]
        if click_with_retries(driver, candidates, attempts=5, delay=0.6):
            logger.info("Clicked KMSI confirmation button")
            return True
        if click_by_xpath_contains_text(driver, 'Yes', timeout=3) or click_by_xpath_contains_text(driver, 'Next', timeout=3):
            logger.info("Clicked KMSI confirmation via text fallback")
            return True
        logger.warning("KMSI confirmation button not found")
        return False

    def click_account_tile(driver, username):
        """Handle account picker screen."""
        candidates = [username, username.split('@')[0], 'Use another account', 'Other account']
        for text in candidates:
            if click_by_xpath_contains_text(driver, text, timeout=3):
                return True
        return False

    def fill_ms_login(driver, username, password):
        """Robust fill for Microsoft login page (prefers password-first)."""
        try:
            click_by_xpath_contains_text(driver, 'Accept', timeout=2)  # cookie banner if any
            maybe_switch_to_login_iframe(driver)

            # Account picker
            click_account_tile(driver, username)

            def visible_el(by, sel, wait=8):
                try:
                    el = WebDriverWait(driver, wait).until(EC.presence_of_element_located((by, sel)))
                    if el.is_displayed():
                        return el
                except Exception:
                    return None
                return None

            # Password first (id=i0118 or name=passwd)
            pwd_input = visible_el(By.ID, 'i0118') or visible_el(By.NAME, 'passwd')

            # Username only if visible (skip hidden moveOffScreen inputs)
            user_input = None
            for by, sel in [(By.NAME, 'loginfmt'), (By.ID, 'i0116')]:
                el = visible_el(by, sel)
                if el:
                    user_input = el
                    break

            # If username visible, fill it then look for password again
            if user_input:
                user_input.clear()
                driver.execute_script("arguments[0].focus();", user_input)
                try:
                    user_input.send_keys(username)
                except Exception:
                    driver.execute_script("arguments[0].value = arguments[1];", user_input, username)
                try:
                    btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'idSIButton9')))
                    driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    pass
                time.sleep(1.0)
                pwd_input = visible_el(By.ID, 'i0118') or visible_el(By.NAME, 'passwd')

            if pwd_input:
                pwd_input.clear()
                driver.execute_script("arguments[0].focus();", pwd_input)
                try:
                    pwd_input.send_keys(password)
                except Exception:
                    driver.execute_script("arguments[0].value = arguments[1];", pwd_input, password)
                try:
                    btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'idSIButton9')))
                    driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    pass
                time.sleep(1.0)
                return True

            logger.error("Password input not found or not interactable.")
            return False
        except Exception as e:
            logger.error(f"MS login fill failed: {e}", exc_info=True)
            return False

    def handle_mfa_code(driver):
        """Fallback path: use verification code instead of Authenticator app."""
        try:
            maybe_switch_to_login_iframe(driver)
            # Step 1: open alternative methods
            try:
                alt_link = WebDriverWait(driver, 6).until(
                    EC.element_to_be_clickable((By.ID, 'signInAnotherWay'))
                )
                driver.execute_script("arguments[0].click();", alt_link)
                logger.info("Clicked 'signInAnotherWay' link")
            except Exception:
                click_by_xpath_contains_text(driver, "I can't use my Microsoft Authenticator app right now", timeout=5)

            # Step 2: choose verification code and wait for OTP input
            candidates = [
                (By.CSS_SELECTOR, "div.table[role='button'][data-value='PhoneAppOTP']", "PhoneAppOTP table role button"),
                (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs div.table[role='button'][data-value='PhoneAppOTP']", "PhoneAppOTP table inside proofs"),
                (By.CSS_SELECTOR, "div[role='button'][data-value='PhoneAppOTP']", "PhoneAppOTP role button"),
                (By.CSS_SELECTOR, "[data-value='PhoneAppOTP']", "PhoneAppOTP data-value"),
                (By.CSS_SELECTOR, "div.row.tile [data-value='PhoneAppOTP']", "row tile data-value PhoneAppOTP"),
                (By.CSS_SELECTOR, "div.row.tile", "row tile"),
                (By.CSS_SELECTOR, "div.row.tile[role='listitem']", "row tile listitem"),
                (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs > div:nth-child(2) > div > div > div.table-cell.text-left.content > div", "provided CSS"),
                (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']/div[2]/div/div/div[2]/div", "provided XPath"),
                (By.XPATH, "/html/body/div/form[1]/div/div/div[2]/div[1]/div/div/div/div/div/div[2]/div[2]/div/div[2]/div/div[2]/div[2]/div[2]/div/div/div[2]/div", "provided absolute XPath"),
                # From user snippet: tile row and text cell
                (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs .table-row", "tile row"),
                (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs .table-row .table-cell.text-left.content", "tile content cell"),
                (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(@class,'table-row')]//div[contains(@class,'text-left')]/div[contains(normalize-space(.), 'Use a verification code')]/ancestor::div[contains(@class,'table-row')][1]", "table-row ancestor of text"),
                (By.XPATH, "//img[contains(@src,'picker_verify_code')]/ancestor::div[contains(@class,'table-row')][1]", "verify-code image row"),
                (By.CSS_SELECTOR, "img[src*='picker_verify_code']", "verify-code img"),
                # broader container clicks
                (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs", "proofs container"),
                (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(normalize-space(.), 'Use a verification code')]/parent::*", "text parent"),
                (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(normalize-space(.), 'Use a verification code')]/parent::div/parent::div", "text grandparent"),
                (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(@class,'table-cell')][.//div[contains(normalize-space(.), 'Use a verification code')]]", "cell containing text"),
            ]

            otp_input = None
            for round_idx in range(2):
                chosen = False
                if click_with_retries(driver, candidates, attempts=6, delay=0.8):
                    chosen = True
                elif click_by_xpath_contains_text(driver, "Use a verification code", timeout=5):
                    chosen = True
                elif click_by_xpath_contains_text(driver, "Use verification code", timeout=5):
                    chosen = True
                else:
                    try:
                        elem = WebDriverWait(driver, 6).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(normalize-space(.), 'Use a verification code')]/ancestor::*[self::button or self::a or @role='button' or @tabindex='0'][1]"))
                        )
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                        driver.execute_script("arguments[0].click();", elem)
                        logger.info("Clicked ancestor container for 'Use a verification code'")
                        chosen = True
                    except Exception:
                        pass

                if not chosen:
                    logger.error("Could not select 'Use a verification code'.")
                    return False

                logger.info("Waiting for OTP input after clicking verification code option...")
                selectors = [
                    (By.NAME, 'otc'),
                    (By.ID, 'idTxtBx_SAOTCC_OTC'),
                    (By.CSS_SELECTOR, 'input[data-testid="verification-entercode-input"]'),
                    (By.CSS_SELECTOR, 'input[name="otc"]'),
                ]
                for by, sel in selectors:
                    try:
                        otp_input = WebDriverWait(driver, 12).until(EC.element_to_be_clickable((by, sel)))
                        break
                    except Exception:
                        continue
                if otp_input:
                    break
                else:
                    logger.warning("OTP input still not visible; retrying click on verification code option...")

            if not otp_input:
                logger.error("OTP input not found after clicking verification code option.")
                return False

            otp_input.clear()
            from local_2fa import get_otp
            otp = get_otp()
            otp_input.send_keys(otp)
            logger.info(f"Filled OTP: {otp}")

            # Verify button candidates
            verify_selectors = [
                (By.ID, 'idSubmit_SAOTCC_Continue'),
                (By.CSS_SELECTOR, '[data-testid="reskin-step-next-button"]'),
            ]
            clicked = False
            for by, sel in verify_selectors:
                try:
                    btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, sel)))
                    driver.execute_script("arguments[0].click();", btn)
                    clicked = True
                    break
                except Exception:
                    continue
            if not clicked:
                if click_by_xpath_contains_text(driver, 'Verify', timeout=5):
                    clicked = True
            if not clicked:
                logger.error("Verify button not found.")
                return False
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"MFA fallback failed: {e}", exc_info=True)
            return False

    def attempt_login(driver, expected_url):
        """Try automatic MS login using stored credentials and OTP."""
        try:
            result = renew_login(driver, expected_url)
            if result:
                return verify_login(driver, expected_url, max_wait_minutes=5)
            return False
        except Exception as e:
            logger.error(f"Auto-login attempt failed: {e}", exc_info=True)
            return False

    def automated_function(event_time, event_name, upcoming_events):
        global attendance_success_count
        script_dir = os.path.dirname(os.path.abspath(__file__))
        user_data_dir = os.path.join(script_dir, 'chrome_user_data')
        os.makedirs(user_data_dir, exist_ok=True)

        driver = initialize_webdriver(user_data_dir)
        if not driver:
            logger.error("WebDriver initialization failed. Exiting function.")
            return False

        try:
            # Use your actual attendance URL
            driver.get("https://generalssb-prod.ec.royalholloway.ac.uk/BannerExtensibility/customPage/page/RHUL_Attendance_Student")
            logger.info("Opened attendance page.")

            expected_url = "https://generalssb-prod.ec.royalholloway.ac.uk/BannerExtensibility/customPage/page/RHUL_Attendance_Student"
            # 尝试自动登录（凭证 + OTP），若已登录则快速通过
            if not attempt_login(driver, expected_url):
                logger.error("Auto-login or verification failed.")
                return False

            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "pbid-blockFoundHappeningNowAttending")))
            logger.info("Attendance page loaded successfully.")

            attending_div = driver.find_element(By.ID, "pbid-blockFoundHappeningNowAttending")
            attending_aria_hidden = attending_div.get_attribute("aria-hidden")

            if attending_aria_hidden == "false":
                current_time = datetime.now(timezone.utc)

                if current_time < event_time:
                    logger.info("Attendance has already been marked, but event time has not occurred yet. Will not update next event.")
                else:
                    logger.info("Attendance has already been marked. Removing event and logging next event.")

                    with events_lock:
                        for event in upcoming_events:
                            if event[0] == event_time and event[1] == event_name:
                                upcoming_events.remove(event)
                                break

                return True
        
            # 如果都找不到按钮，才报错
            if click_button_if_visible(driver, ["pbid-buttonFoundHappeningNowButtonsOneHere", "pbid-buttonFoundHappeningNowButtonsTwoHere"]):
                logger.info("Successfully clicked attendance button.")
            else:
                logger.warning("No clickable button found. Ending function.")
                return False

            # Verify that attendance has been marked
            time.sleep(2)  # Wait for any potential page updates
            attending_div = driver.find_element(By.ID, "pbid-blockFoundHappeningNowAttending")
            attending_aria_hidden = attending_div.get_attribute("aria-hidden")
            if attending_aria_hidden == "false":
                logger.info("Attendance successfully marked.")
                with counter_lock:
                    attendance_success_count += 1

                with events_lock:
                    for event in upcoming_events:
                        if event[0] == event_time and event[1] == event_name:
                            upcoming_events.remove(event)
                            break
                return True
            else:
                logger.error("Failed to confirm attendance after clicking.")
                return False

        except Exception as e:
            logger.error(f"Failed during attendance marking: {e}", exc_info=True)
            return False
        finally:
            driver.quit()
            # Log the next event
            with events_lock:
                if upcoming_events:
                    next_event_start, next_event_name, _, next_event_end = upcoming_events[0]
                    local_next_event_start = next_event_start.astimezone()
                    duration = next_event_end - next_event_start
                    logger.info(
                        f"Waiting for next event: [bold magenta]{next_event_name}[/bold magenta] at "
                        f"[bold cyan]{local_next_event_start.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan] "
                        f"(duration: [bold green]{str(duration).split('.')[0]}[/bold green])"
                    )
                else:
                    logger.info("No further upcoming events.")

    def load_calendar(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                calendar = Calendar(f.read())
            return calendar
        except FileNotFoundError:
            logger.error(f"Calendar file not found: {file_path}")
            return None
        except Exception as e:
            logger.error(f"Error loading calendar: {e}", exc_info=True)
            return None

    def get_upcoming_events(calendar):
        now = datetime.now(timezone.utc)
        upcoming_events = []
        for event in calendar.events:
            # Convert event start and end times to UTC
            event_start = event.begin.to('UTC').datetime
            event_end = event.end.to('UTC').datetime
            event_name = event.name
            trigger_time = calculate_trigger_time(event_start)
            if event_start > now and 'Optional Attendance' not in event_name:
                upcoming_events.append((event_start, event_name, trigger_time, event_end))
        upcoming_events.sort(key=lambda x: x[2])  # Sort by trigger_time
        return upcoming_events

    def calculate_trigger_time(event_time):
        minutes_after = random.randint(3, 8)
        trigger_time = event_time + timedelta(minutes=minutes_after)
        return trigger_time

    def wait_and_trigger(upcoming_events, exit_event):
        # Log the next event at the beginning
        with events_lock:
            if upcoming_events:
                next_event_start, next_event_name, _, next_event_end = upcoming_events[0]
                local_next_event_start = next_event_start.astimezone()
                duration = next_event_end - next_event_start
                logger.info(
                    f"Waiting for next event: [bold magenta]{next_event_name}[/bold magenta] at "
                    f"[bold cyan]{local_next_event_start.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan] "
                    f"(duration: [bold green]{str(duration).split('.')[0]}[/bold green])"
                )

        logger.info("Waiting in the background for events to trigger...")
        while not exit_event.is_set():
            now = datetime.now(timezone.utc)
            with events_lock:
                if not upcoming_events:
                    logger.info("All events have been processed, exiting the script.")
                    exit_event.set()
                    break
                event = upcoming_events[0]
                event_time, event_name, trigger_time, event_end = event
                if now >= trigger_time.astimezone(timezone.utc):
                    local_event_time = event_time.astimezone()
                    logger.info(
                        f"[bold red]Triggering event:[/bold red] [bold magenta]{event_name}[/bold magenta] at "
                        f"[bold cyan]{local_event_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]"
                    )
                    # Run automated_function in a new thread
                    threading.Thread(target=automated_function, args=(event_time, event_name, upcoming_events), daemon=True).start()
                    # Event processed, remove it
                    upcoming_events.pop(0)
                else:
                    sleep_duration = max((trigger_time - now).total_seconds(), 0)
            if exit_event.wait(timeout=min(sleep_duration, 60)):
                break

    def listen_for_keypress(upcoming_events, exit_event):
        ctrl_pressed = [False]  # Use a mutable object to share state

        def on_press(key):
            try:
                if key.char == '[':
                    ctrl_pressed[0] = True
                elif key.char == ']':
                    if ctrl_pressed[0]:
                        with events_lock:
                            if upcoming_events:
                                next_event_time, next_event_name, _, next_event_end = upcoming_events[0]
                                logger.info(
                                    f"[bold magenta]Manually triggered automation for:[/bold magenta] [bold magenta]{next_event_name}[/bold magenta]"
                                )
                                # Run automated_function in a new thread
                                threading.Thread(target=automated_function, args=(next_event_time, next_event_name, upcoming_events), daemon=True).start()
                            else:
                                logger.warning("No upcoming events to process.")
                elif key.char == 'q':
                    if ctrl_pressed[0]:
                        logger.info("Exit shortcut pressed. Terminating the script.")
                        exit_event.set()
            except AttributeError:
                pass

        def on_release(key):
            try:
                if key.char == '[':
                    ctrl_pressed[0] = False
            except AttributeError:
                pass

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        while not exit_event.is_set():
            time.sleep(1)
        listener.stop()

    def get_single_ics_file():
        ics_folder = os.path.join(script_dir, 'ics')
        if not os.path.exists(ics_folder):
            os.makedirs(ics_folder, exist_ok=True)
            logger.info(f"Created folder '{ics_folder}' as it did not exist.")

        ics_files = [os.path.join(ics_folder, file) for file in os.listdir(ics_folder) if file.endswith('.ics')]
        if len(ics_files) == 0:
            logger.error("Error: No .ics file found.")
            return None
        elif len(ics_files) > 1:
            logger.error("Error: Multiple .ics files found, please ensure only one file is in the ics folder.")
            return None
        else:
            return ics_files[0]

    def get_runtime_duration():
        delta = datetime.now() - start_time
        return str(delta).split('.')[0]

    def get_git_info():
        """Return (hash, date, count) for current HEAD; fallback to unknown."""
        try:
            commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], cwd=script_dir).decode().strip()
            commit_date = subprocess.check_output(['git', 'show', '-s', '--format=%cd', '--date=iso-strict', 'HEAD'], cwd=script_dir).decode().strip()
            commit_count = subprocess.check_output(['git', 'rev-list', '--count', 'HEAD'], cwd=script_dir).decode().strip()
            return commit, commit_date, commit_count
        except Exception:
            return "unknown", "unknown", "unknown"

    def update_display(exit_event):
        git_commit, git_date, git_count = get_git_info()
        with Live(refresh_per_second=1, console=console, screen=True) as live:
            while not exit_event.is_set():
                with counter_lock:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    runtime = get_runtime_duration()
                    attendance = attendance_success_count

                with log_buffer_lock:
                    latest_logs = list(log_buffer)

                info_table = Table.grid(expand=True)
                info_table.add_row(
                    f"[bold cyan]Current Time:[/bold cyan] {current_time}",
                    f"[bold green]Runtime Duration:[/bold green] {runtime}",
                    f"[bold yellow]Attendance Success Count:[/bold yellow] {attendance}",
                    f"[bold magenta]PandaQuQ:[/bold magenta] [link=https://github.com/PandaQuQ/RHUL_attendance_bot]GitHub Repo[/link]"
                )

                log_content = "\n".join(latest_logs) if latest_logs else "No logs available."
                log_panel = Panel(log_content, title="[bold green]Latest Logs[/bold green]", border_style="green", padding=(1, 2))

                instructions = Text.from_markup(
                    "Press [yellow][[/yellow] then [yellow]][/yellow] to manually trigger the next event\n"
                    "Press [yellow][[/yellow] then [yellow]q[/yellow] to exit the script",
                    justify="center",
                )
                shortcut_instructions = Align.center(instructions, vertical="middle")

                version_text = Align.center(f"Version: {git_commit} ({git_date})", vertical="middle")
                commit_count_text = Align.center(f"This is the No.[red]{git_count}[/red] version", vertical="middle")

                layout = Table.grid(expand=True)
                layout.add_row(info_table)
                layout.add_row(log_panel)
                layout.add_row(shortcut_instructions)
                layout.add_row(version_text)
                layout.add_row(commit_count_text)

                live.update(layout)
                if exit_event.wait(timeout=1):
                    break

    def check_system_time():
        try:
            client = ntplib.NTPClient()
            response = client.request('pool.ntp.org')
            system_time = datetime.now(timezone.utc).timestamp()
            ntp_time = response.tx_time
            time_difference = abs(system_time - ntp_time)
            if time_difference > 5:
                logger.warning(f"System time is off by {time_difference} seconds. Consider synchronizing your clock.")
            else:
                logger.info("System time is synchronized with NTP server.")
        except Exception as e:
            logger.error(f"Failed to check system time: {e}", exc_info=True)

    def check_for_updates():
        try:
            local_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
            remote_commit = subprocess.check_output(['git', 'ls-remote', 'origin', 'HEAD']).decode().split()[0]
            if local_commit != remote_commit:
                logger.info("New update detected.")
                # Prompt the user in the console
                print("A new update is available. Do you want to update now? (y/n): ", end='')
                user_input = input().strip().lower()
                if user_input == '' or user_input == 'y':
                    logger.info("Updating the script...")
                    subprocess.check_call(['git', 'pull'])
                    logger.info("Update successful. Restarting the script...")
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                else:
                    logger.info("Skipping update. Continuing with the current version.")
            else:
                logger.info("No updates found. Continuing execution.")
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}", exc_info=True)

    try:
        check_for_updates()
        check_system_time()

        ics_file = get_single_ics_file()
        if not ics_file:
            logger.info("Program terminated due to missing or multiple .ics files.")
            return

        calendar = load_calendar(ics_file)
        if not calendar:
            logger.error("Failed to load calendar. Exiting.")
            return

        upcoming_events = get_upcoming_events(calendar)
        if not upcoming_events:
            logger.info("No upcoming events.")
            return

        # Start threads with exit_event
        display_thread = threading.Thread(target=update_display, args=(exit_event,), daemon=True)
        keypress_thread = threading.Thread(target=listen_for_keypress, args=(upcoming_events, exit_event), daemon=True)
        display_thread.start()
        keypress_thread.start()

        wait_and_trigger(upcoming_events, exit_event)
        exit_event.set()
        display_thread.join(timeout=3)
        keypress_thread.join(timeout=3)

    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
        exit_event.set()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        exit_event.set()
    finally:
        try:
            display_thread.join(timeout=3)
            keypress_thread.join(timeout=3)
        except Exception:
            pass

if __name__ == "__main__":
    main()
