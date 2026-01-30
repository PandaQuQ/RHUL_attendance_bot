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

CREDENTIALS_FILE = 'credentials.json'
TIMETABLE_URL = 'https://webtimetables.royalholloway.ac.uk/'


def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        raise RuntimeError('Missing credentials.json')
    with open(CREDENTIALS_FILE, 'r') as f:
        return json.load(f)

def start_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def fetch_ics_url():
    creds = load_credentials()
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
                ics_folder = os.path.join(os.getcwd(), 'ics')
                os.makedirs(ics_folder, exist_ok=True)
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

if __name__ == '__main__':
    fetch_ics_url()
