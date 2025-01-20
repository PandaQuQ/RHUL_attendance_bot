import os
import sys
import subprocess
import logging
import threading
import time
import random
import shutil
from datetime import datetime, timedelta, timezone
from collections import deque
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
                # Use JavaScript click to improve reliability
                driver.execute_script("arguments[0].click();", button)
                logger.info(f"Clicked button: {button_id}")
                button_flag = True
                return True
            except Exception as e:
                pass
        if button_flag == False:
            logger.error(f"Error clicking buttons: Can't find any button", exc_info=True)
        logger.warning("No clickable button found.")
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
            if not verify_login(driver, expected_url, max_wait_minutes=30):
                logger.error("Login verification failed.")
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

    def update_display(exit_event):
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

                shortcut_instructions = Align.center(
                    "Press [yellow][[/yellow] then [yellow]][/yellow] to manually trigger the next event.\n"
                    "Press [yellow][[/yellow] then [yellow]q[/yellow] to exit the script.\n"
                    "You may need to trigger manually the first time to log in.",
                    vertical="middle"
                )

                layout = Table.grid(expand=True)
                layout.add_row(info_table)
                layout.add_row(log_panel)
                layout.add_row(shortcut_instructions)

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
        display_thread.start()
        keypress_thread = threading.Thread(target=listen_for_keypress, args=(upcoming_events, exit_event), daemon=True)
        keypress_thread.start()
        wait_and_trigger(upcoming_events, exit_event)

    except KeyboardInterrupt:
        logger.info("Script terminated by user.")
        exit_event.set()
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        exit_event.set()

if __name__ == "__main__":
    main()
