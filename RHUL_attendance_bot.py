import os
import random
import time
import threading
import logging
import platform
import sys
from datetime import datetime, timedelta, timezone
from ics import Calendar
from rich.console import Console
from rich.panel import Panel
from rich import box
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
import tkinter as tk
from tkinter import messagebox
import webbrowser
from collections import deque
import keyboard

# Initialize Rich console
console = Console()

# Create a logger
logger = logging.getLogger("rich")
logger.setLevel(logging.DEBUG)  # Set the lowest log level to DEBUG to capture all messages

# Create a file handler to log INFO and above messages with timestamps
file_handler = logging.FileHandler('automation.log', encoding='utf-8', mode='a')
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Create a fixed-size deque to store the latest five log messages
log_buffer = deque(maxlen=5)
log_buffer_lock = threading.Lock()

# Create a custom BufferLogHandler to store logs in the deque
class BufferLogHandler(logging.Handler):
    def __init__(self, buffer, buffer_lock):
        super().__init__()
        self.buffer = buffer
        self.buffer_lock = buffer_lock

    def emit(self, record):
        log_entry = self.format(record)
        with self.buffer_lock:
            self.buffer.append(log_entry)

# Configure BufferLogHandler to only display the message content without timestamps and levels
buffer_handler = BufferLogHandler(log_buffer, log_buffer_lock)
buffer_handler.setLevel(logging.INFO)
buffer_formatter = logging.Formatter('%(message)s')  # Only message content
buffer_handler.setFormatter(buffer_formatter)
logger.addHandler(buffer_handler)

# Initialize global variables
start_time = datetime.now()
attendance_success_count = 0

# Lock for thread-safe updates to the counter
counter_lock = threading.Lock()

def verify_login(driver, expected_url, max_wait_minutes=30):
    """
    Verifies if the script is logged in by checking the current URL.
    If not logged in, logs "Need to login" and checks every 10 seconds until logged in or max wait time is reached.
    
    Args:
        driver (webdriver.Chrome): The Selenium WebDriver instance.
        expected_url (str): The URL that indicates a successful login.
        max_wait_minutes (int): Maximum minutes to wait for login. Default is 30 minutes.
    
    Returns:
        bool: True if logged in within the wait time, False otherwise.
    """
    initial_wait = 3  # seconds
    periodic_wait = 10  # seconds
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
            logger.info("Need to login.")
    
    logger.error(f"Login not detected after {max_wait_minutes} minutes.")
    return False

def initialize_webdriver(user_data_dir):
    """
    Initializes the Chrome WebDriver using webdriver_manager.
    Automatically installs the appropriate ChromeDriver version if not present.
    
    Args:
        user_data_dir (str): Path to the Chrome user data directory.
    
    Returns:
        webdriver.Chrome: An instance of Chrome WebDriver.
    """
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # Hide DevTools listening log

    try:
        # Use Service to manage ChromeDriver installation and execution
        service = Service(ChromeDriverManager().install())  # Automatically manage the driver

        # Ensure webdriver.Chrome only receives 'service' and 'options'
        driver = webdriver.Chrome(service=service, options=chrome_options)  # Correct instantiation
        logger.info("Chrome WebDriver initialized successfully.")
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome WebDriver: {e}")
        return None

def click_button_if_visible(driver, button_id):
    """If the button is clickable, click it and return True; otherwise, return False."""
    try:
        button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, button_id)))
        button.click()
        logger.info(f"Clicked button: {button_id}")
        return True
    except Exception as e:
        logger.error(f"Error clicking button {button_id}: {e}")
        return False

def automated_function(next_event_time, next_event_name, upcoming_events):
    global attendance_success_count
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, 'chrome_user_data')
    os.makedirs(user_data_dir, exist_ok=True)

    # Initialize WebDriver using the updated function
    driver = initialize_webdriver(user_data_dir)
    if not driver:
        logger.error("WebDriver initialization failed. Exiting function.")
        return False

    try:
        # Navigate to the attendance page
        driver.get("https://generalssb-prod.ec.royalholloway.ac.uk/BannerExtensibility/customPage/page/RHUL_Attendance_Student")
        logger.info("Opened attendance page.")

        # Verify login before proceeding
        expected_url = "https://generalssb-prod.ec.royalholloway.ac.uk/BannerExtensibility/customPage/page/RHUL_Attendance_Student"
        if not verify_login(driver, expected_url, max_wait_minutes=30):
            logger.error("Login verification failed.")
            driver.quit()
            return False

        # Proceed with attendance marking after successful login
        # Wait for the page to load completely
        WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "pbid-blockFoundHappeningNowAttending")))
        logger.info("Attendance page loaded successfully.")

        # Check if attendance has already been marked
        attending_div = driver.find_element(By.ID, "pbid-blockFoundHappeningNowAttending")
        attending_aria_hidden = attending_div.get_attribute("aria-hidden")
        logger.debug(f"'pbid-blockFoundHappeningNowAttending' aria-hidden: {attending_aria_hidden}")

        if attending_aria_hidden == "false":
            logger.info("Attendance has already been marked. Returning without further action.")
            # 获取下一个事件的名称和时间
            next_index = upcoming_events.index((next_event_time, next_event_name))
            if next_index < len(upcoming_events):
                next_event_time, next_event_name = upcoming_events[next_index]
                local_next_event_time = next_event_time.astimezone()

                # 显示下一个事件的信息，保持颜色格式
                logger.info(f"[bold red]Next event:[/bold red] [bold yellow]{next_event_name}[/bold yellow] ")
                logger.info(f"scheduled for [bold cyan]{local_next_event_time}[/bold cyan]")
            else:
                logger.info("No further upcoming events.")
            \
            driver.quit()
            return True

        # Try clicking the attendance buttons
        if click_button_if_visible(driver, "pbid-buttonFoundHappeningNowButtonsTwoHere"):
            pass
        elif click_button_if_visible(driver, "pbid-buttonFoundHappeningNowButtonsOneHere"):
            pass
        else:
            logger.warning("No clickable button found. Ending function.")
            driver.quit()
            return False

        # Wait for the page status to update
        WebDriverWait(driver, 10).until(EC.url_to_be(expected_url))

        if driver.current_url == expected_url:
            logger.info("Successfully marked attendance.")
            with counter_lock:
                attendance_success_count += 1  # Increment success count
            driver.quit()
            return True
        else:
            logger.error("Failed to mark attendance, check the URL.")
            driver.quit()
            return False

    except Exception as e:
        logger.error(f"Failed during attendance marking: {e}")
        logger.debug("Page source for debugging:\n" + driver.page_source)
        driver.quit()
        return False

def load_calendar(file_path):
    """Load an .ics calendar file and parse events."""
    try:
        with open(file_path, 'r') as f:
            calendar = Calendar(f.read())
        return calendar
    except FileNotFoundError:
        logger.error(f"Calendar file not found: {file_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading calendar: {e}")
        return None

def get_upcoming_events(calendar):
    """Get all upcoming events, excluding those with 'Optional Attendance' in their name."""
    now = datetime.now(timezone.utc)
    upcoming_events = []
    for event in calendar.events:
        event_start = event.begin.datetime
        event_name = event.name
        if event_start > now and 'Optional Attendance' not in event_name:
            upcoming_events.append((event_start, event_name))
    upcoming_events.sort(key=lambda x: x[0])
    return upcoming_events

def calculate_trigger_time(event_time):
    """Calculate trigger time (a random time between 3-8 minutes after event start)."""
    minutes_after = random.randint(3, 8)
    if event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=timezone.utc)
    trigger_time = event_time + timedelta(minutes=minutes_after)
    return trigger_time

def wait_and_trigger(upcoming_events):
    """Wait in the background and trigger automation at the appropriate time."""
    logger.info("Waiting in the background for events to trigger...")
    while True:
        now = datetime.now(timezone.utc)
        for event_time, event_name in list(upcoming_events):
            trigger_time = calculate_trigger_time(event_time)
            if event_time <= now <= trigger_time:
                logger.info(f"The event '{event_name}' scheduled at {event_time}, executing the automated function...")
                if automated_function(event_time, event_name, upcoming_events):
                    upcoming_events.remove((event_time, event_name))
                else:
                    logger.warning("No action taken. Rechecking calendar for upcoming events.")
                    return

        if not upcoming_events:
            logger.info("All events have been processed, exiting the script.")
            break

        # Dynamically calculate the next sleep duration to optimize efficiency
        next_event_time, _ = upcoming_events[0]
        trigger_time = calculate_trigger_time(next_event_time)
        sleep_duration = (trigger_time - now).total_seconds()
        sleep_duration = max(sleep_duration, 60)  # Minimum sleep of 60 seconds
        time.sleep(sleep_duration)

def listen_for_keypress(upcoming_events):
    """Listen for the '[' and ']' keys to manually trigger automation."""
    while True:
        try:
            if keyboard.is_pressed('[') and keyboard.is_pressed(']'):
                if upcoming_events:
                    next_event_time, next_event_name = upcoming_events[0]
                    automated_function(next_event_time, next_event_name, upcoming_events)
                else:
                    logger.warning("No upcoming events to process.")
                time.sleep(1)  # Prevent repeated triggers
        except:
            continue

def get_single_ics_file():
    """Retrieve the single .ics file path from the './ics' directory."""
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
    """Calculate the runtime duration."""
    delta = datetime.now() - start_time
    return str(delta).split('.')[0]  # Remove microseconds

def update_display():
    """Use Rich Live to update the display, including fixed information, latest five log messages, and shortcut key instructions."""
    with Live(refresh_per_second=1, console=console, screen=True) as live:
        while True:
            with counter_lock:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                runtime = get_runtime_duration()
                attendance = attendance_success_count

            # Retrieve the latest five log messages
            with log_buffer_lock:
                latest_logs = list(log_buffer)

            # Create the fixed information table
            info_table = Table.grid(expand=True)
            info_table.add_row(
                f"[bold cyan]Current Time:[/bold cyan] {current_time}",
                f"[bold green]Runtime Duration:[/bold green] {runtime}",
                f"[bold yellow]Attendance Success Count:[/bold yellow] {attendance}",
                f"[bold magenta]PandaQuQ:[/bold magenta] [link=https://github.com/PandaQuQ]https://github.com/PandaQuQ[/link]"
            )

            # Create the log display panel (five lines), left-aligned
            if latest_logs:
                log_content = "\n".join(latest_logs)
            else:
                log_content = "No logs available."

            log_panel = Panel(log_content, title="Latest Logs", border_style="green", padding=(1, 2))

            # Create the shortcut key instruction line, center-aligned
            shortcut_instructions = Align.center(
                "Press [yellow][[/yellow] and [yellow]][/yellow] together to trigger automation.",
                vertical="middle"
            )
            first_instructions = Align.center(
                "Do it for the first time for login",
                vertical="middle"
            )

            # Create the overall layout
            layout = Table.grid(expand=True)
            layout.add_row(info_table)
            layout.add_row(log_panel)
            layout.add_row(shortcut_instructions)  # Add the shortcut instruction as a new row
            layout.add_row(first_instructions)  # Add the 1st login instruction as a new row

            # Update the Live display
            live.update(layout)
            time.sleep(1)

def main():
    """Main function to load the calendar and start listening and triggering events."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    user_data_dir = os.path.join(script_dir, 'chrome_user_data')
    os.makedirs(user_data_dir, exist_ok=True)

    try:
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

        next_event_time, next_event_name = upcoming_events[0]
        local_next_event_time = next_event_time.astimezone()
        logger.info(f"The next event is '{next_event_name}' scheduled for {local_next_event_time}.")

        # Start the display update thread
        threading.Thread(target=update_display, daemon=True).start()

        # Start the keypress listening thread
        threading.Thread(target=listen_for_keypress, args=(upcoming_events,), daemon=True).start()

        # Begin waiting and triggering events
        wait_and_trigger(upcoming_events)
    except KeyboardInterrupt:
        logger.info("Script terminated by user.")

if __name__ == "__main__":
    main()
