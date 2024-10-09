import os
import sys
import subprocess
import threading
import time
import random
import logging
from datetime import datetime, timedelta, timezone
from ics import Calendar
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich import box
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pynput import keyboard
from collections import deque

# Initialize Rich console
console = Console()

# Create a logger
logger = logging.getLogger("rich")
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
start_time = datetime.now()
attendance_success_count = 0

# Lock for thread-safe updates to the counter
counter_lock = threading.Lock()

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

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Chrome WebDriver initialized successfully.")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        return None

def click_button_if_visible(driver, button_id):
    try:
        button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, button_id)))
        button.click()
        logger.info(f"Clicked button: {button_id}")
        return True
    except Exception as e:
        logger.error(f"Error clicking button {button_id}: {e}")
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
            driver.quit()
            return False

        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "pbid-blockFoundHappeningNowAttending")))
        logger.info("Attendance page loaded successfully.")

        attending_div = driver.find_element(By.ID, "pbid-blockFoundHappeningNowAttending")
        attending_aria_hidden = attending_div.get_attribute("aria-hidden")

        if attending_aria_hidden == "false":
            current_time = datetime.now(timezone.utc)

            if current_time < event_time:
                # 当前时间早于事件时间，不更新事件列表
                logger.info("Attendance has already been marked, but event time has not occurred yet. Will not update next event.")
            else:
                # 当前时间晚于事件时间，移除事件并记录下一个事件
                logger.info("Attendance has already been marked. Removing event and logging next event.")

                if (event_time, event_name) in upcoming_events:
                    upcoming_events.remove((event_time, event_name))

            if upcoming_events:
                next_event_time, next_event_name = upcoming_events[0]
                local_next_event_time = next_event_time.astimezone()
                logger.info(f"[bold red]Next event:[/bold red] [bold yellow]{next_event_name}[/bold yellow] scheduled for [bold cyan]{local_next_event_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]")
            else:
                logger.info("No further upcoming events.")

            driver.quit()
            return True

        if click_button_if_visible(driver, "pbid-buttonFoundHappeningNowButtonsTwoHere") or \
           click_button_if_visible(driver, "pbid-buttonFoundHappeningNowButtonsOneHere"):
            logger.info("Successfully clicked attendance button.")
        else:
            logger.warning("No clickable button found. Ending function.")
            driver.quit()
            return False

        WebDriverWait(driver, 10).until(EC.url_to_be(expected_url))
        if driver.current_url == expected_url:
            logger.info("Successfully marked attendance.")
            with counter_lock:
                attendance_success_count += 1

            # 移除当前事件并记录下一个事件
            if (event_time, event_name) in upcoming_events:
                upcoming_events.remove((event_time, event_name))

            if upcoming_events:
                next_event_time, next_event_name = upcoming_events[0]
                local_next_event_time = next_event_time.astimezone()
                logger.info(f"[bold red]Next event:[/bold red] [bold yellow]{next_event_name}[/bold yellow] scheduled for [bold cyan]{local_next_event_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]")
            else:
                logger.info("No further upcoming events.")

            driver.quit()
            return True
        else:
            logger.error("Failed to mark attendance, check the URL.")
            driver.quit()
            return False

    except Exception as e:
        logger.error(f"Failed during attendance marking: {e}")
        driver.quit()
        return False


def load_calendar(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            calendar = Calendar(f.read())
        return calendar
    except FileNotFoundError:
        logger.error(f"Calendar file not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading calendar: {e}")
        return None

def get_upcoming_events(calendar):
    now = datetime.now(timezone.utc)
    upcoming_events = []
    for event in calendar.events:
        event_start = event.begin.datetime
        event_name = event.name
        if event_start.tzinfo is None:
            event_start = event_start.replace(tzinfo=timezone.utc)
        if event_start > now and 'Optional Attendance' not in event_name:
            upcoming_events.append((event_start, event_name))
    upcoming_events.sort(key=lambda x: x[0])
    return upcoming_events

def calculate_trigger_time(event_time):
    minutes_after = random.randint(3, 8)
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    trigger_time = event_time + timedelta(minutes=minutes_after)
    return trigger_time

def wait_and_trigger(upcoming_events):
    logger.info("Waiting in the background for events to trigger...")
    while True:
        now = datetime.now(timezone.utc)
        for event_time, event_name in list(upcoming_events):
            trigger_time = calculate_trigger_time(event_time)
            if now >= trigger_time:
                local_event_time = event_time.astimezone()
                logger.info(f"[bold red]Triggering event:[/bold red] [bold yellow]{event_name}[/bold yellow] at [bold cyan]{local_event_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]")
                if automated_function(event_time, event_name, upcoming_events):
                    # Event processed, continue to next
                    pass
                else:
                    logger.warning("Automated function failed. Retrying later.")
            else:
                sleep_duration = (trigger_time - now).total_seconds()
                time.sleep(min(sleep_duration, 60))
        if not upcoming_events:
            logger.info("All events have been processed, exiting the script.")
            break

def listen_for_keypress(upcoming_events):
    def on_press(key):
        try:
            if key.char == '[':
                listener.ctrl_pressed = True
            elif key.char == ']':
                if listener.ctrl_pressed and upcoming_events:
                    next_event_time, next_event_name = upcoming_events[0]
                    logger.info(f"[bold magenta]Manually triggered automation for:[/bold magenta] [bold yellow]{next_event_name}[/bold yellow]")
                    if automated_function(next_event_time, next_event_name, upcoming_events):
                        # Event processed, continue to next
                        pass
                else:
                    logger.warning("No upcoming events to process.")
        except AttributeError:
            pass

    def on_release(key):
        try:
            if key.char == '[':
                listener.ctrl_pressed = False
        except AttributeError:
            pass

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.ctrl_pressed = False
        listener.join()

def get_single_ics_file():
    ics_folder = './ics'
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

def update_display():
    with Live(refresh_per_second=1, console=console, screen=True) as live:
        while True:
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
                "Press [yellow][[/yellow] and [yellow]][/yellow] together to trigger automation.\nDo it for the first time for login.",
                vertical="middle"
            )

            layout = Table.grid(expand=True)
            layout.add_row(info_table)
            layout.add_row(log_panel)
            layout.add_row(shortcut_instructions)

            live.update(layout)
            time.sleep(1)

def check_for_updates():
    try:
        local_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
        remote_commit = subprocess.check_output(['git', 'ls-remote', 'origin', 'HEAD']).decode().split()[0]
        if local_commit != remote_commit:
            logger.info("New update detected.")
            user_input = input("A new update is available. Do you want to update now? (y/n): ").strip().lower()
            if user_input == 'y':
                logger.info("Updating the script...")
                subprocess.check_call(['git', 'pull'])
                logger.info("Update successful. Restarting the script...")
                os.execv(sys.executable, [sys.executable] + sys.argv)
            else:
                logger.info("Skipping update. Continuing with the current version.")
        else:
            logger.info("No updates found. Continuing execution.")
    except Exception as e:
        logger.error(f"Failed to check for updates: {e}")

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, 'chrome_user_data')
    os.makedirs(user_data_dir, exist_ok=True)

    try:
        check_for_updates()

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

        if upcoming_events:
            next_event_time, next_event_name = upcoming_events[0]
            local_next_event_time = next_event_time.astimezone()
            logger.info(f"[bold red]Next event:[/bold red] [bold yellow]{next_event_name}[/bold yellow] scheduled for [bold cyan]{local_next_event_time.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]")

        threading.Thread(target=update_display, daemon=True).start()
        threading.Thread(target=listen_for_keypress, args=(upcoming_events,), daemon=True).start()

        wait_and_trigger(upcoming_events)
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")

if __name__ == "__main__":
    main()
