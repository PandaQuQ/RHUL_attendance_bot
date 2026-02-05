import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from app_paths import get_credentials_path, get_ics_dir, prompt_select_profile, profile_exists
TIMETABLE_URL = 'https://webtimetables.royalholloway.ac.uk/'


def load_credentials(profile_name=None):
    credentials_path = get_credentials_path(profile_name)
    if not os.path.exists(credentials_path):
        raise RuntimeError('Missing credentials.json')
    with open(credentials_path, 'r') as f:
        return json.load(f)

def start_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_ics_url(profile_name=None):
    creds = load_credentials(profile_name)
    username = creds['username'].split('@')[0]
    password = creds['password']
    driver = start_driver()
    driver.get(TIMETABLE_URL)
    try:
        # Login
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'tUserName')))
        driver.find_element(By.ID, 'tUserName').send_keys(username)
        driver.find_element(By.ID, 'tPassword').send_keys(password)
        driver.find_element(By.ID, 'bLogin').click()
        time.sleep(2)
        # Click My Timetable
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'LinkBtn_studentMyTimetable')))
        driver.find_element(By.ID, 'LinkBtn_studentMyTimetable').click()
        time.sleep(1)
        # Select weeks: Autumn, Spring & Summer Term
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'lbWeeks')))
        select_weeks = Select(driver.find_element(By.ID, 'lbWeeks'))
        select_weeks.select_by_value('2;3;4;5;6;7;8;9;10;11;12;18;19;20;21;22;23;24;25;26;27;28;33;34;35;36;37;38')
        time.sleep(1)
        # Select iCal radio
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'RadioType_2')))
        driver.find_element(By.ID, 'RadioType_2').click()
        time.sleep(1)
        # Click View Timetable
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'bGetTimetable')))
        driver.find_element(By.ID, 'bGetTimetable').click()
        time.sleep(1)
        # Click Android link
        WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.ID, 'android')))
        driver.find_element(By.ID, 'android').click()
        time.sleep(1)
        # Extract iCal URL
        ical_url = None
        strongs = driver.find_elements(By.TAG_NAME, 'strong')
        for s in strongs:
            text = s.text.strip()
            if text.startswith('https://webtimetables.royalholloway.ac.uk/ical/default.aspx?'):
                ical_url = text
                break
        if ical_url:
            print(f'iCal URL: {ical_url}')
            # Download the .ics file
            import requests
            # Campus site has broken/unknown cert; disable verification for this download.
            requests.packages.urllib3.disable_warnings()  # suppress InsecureRequestWarning
            response = requests.get(ical_url, verify=False)
            if response.status_code == 200:
                ics_folder = get_ics_dir(profile_name)
                ics_path = os.path.join(ics_folder, 'student_timetable.ics')
                with open(ics_path, 'wb') as f:
                    f.write(response.content)
                print(f'.ics file saved to {ics_path}')
            else:
                print(f'Failed to download .ics file. Status code: {response.status_code}')
        else:
            print('Could not find iCal URL on the page.')
    except Exception as e:
        print(f'Error during timetable automation: {e}')
    finally:
        time.sleep(5)
        driver.quit()


def refresh_calendar(profile_name=None, load_calendar_fn=None, get_upcoming_events_fn=None, logger=None):
    def _log(msg, level="info"):
        if logger:
            try:
                getattr(logger, level)(msg)
                return
            except Exception:
                pass
        print(msg)

    ics_path = os.path.join(get_ics_dir(profile_name), 'student_timetable.ics')
    try:
        if os.path.exists(ics_path):
            os.remove(ics_path)
        fetch_ics_url(profile_name=profile_name)

        if load_calendar_fn and get_upcoming_events_fn:
            calendar = load_calendar_fn(ics_path)
            if not calendar:
                _log("Failed to reload calendar after refresh.", level="error")
                return None, ics_path
            new_events = get_upcoming_events_fn(calendar)
            return new_events, ics_path
        return None, ics_path
    except Exception as e:
        _log(f"Failed to refresh calendar: {e}", level="error")
        return None, ics_path


def renew_calendar(upcoming_events, events_lock, profile_name=None, load_calendar_fn=None, get_upcoming_events_fn=None, logger=None):
    new_events, _ = refresh_calendar(
        profile_name=profile_name,
        load_calendar_fn=load_calendar_fn,
        get_upcoming_events_fn=get_upcoming_events_fn,
        logger=logger,
    )
    if new_events is None:
        return
    with events_lock:
        upcoming_events.clear()
        upcoming_events.extend(new_events)
    if new_events:
        next_event_start, next_event_name, _, next_event_end = new_events[0]
        local_next_event_start = next_event_start.astimezone()
        duration = next_event_end - next_event_start
        msg = (
            f"Waiting for next event: [bold magenta]{next_event_name}[/bold magenta] at "
            f"[bold cyan]{local_next_event_start.strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan] "
            f"(duration: [bold green]{str(duration).split('.')[0]}[/bold green])"
        )
        if logger:
            logger.info(msg)
        else:
            print(msg)
    else:
        if logger:
            logger.info("No upcoming events after refresh.")
        else:
            print("No upcoming events after refresh.")

    if logger:
        logger.info("Calendar refreshed successfully.", extra={"gray": True})
    else:
        print("Calendar refreshed successfully.")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="RHUL timetable ICS fetcher")
    parser.add_argument("-help", action="help", help="Show this help message and exit")
    parser.add_argument("-user", "--user", dest="profile", default=None, help="Profile name")
    args = parser.parse_args()
    if args.profile:
        if not profile_exists(args.profile):
            print("Profile not exist.")
            raise SystemExit(1)
        profile_name = args.profile
    else:
        profile_name = prompt_select_profile()
    fetch_ics_url(profile_name=profile_name)
