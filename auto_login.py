

import os
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from local_2fa import bind, get_otp

CONFIG_FILE = '2fa_config.json'
CREDENTIALS_FILE = 'credentials.json'
SECURITY_INFO_URL = 'https://mysignins.microsoft.com/security-info'
LOGIN_URL = 'https://mysignins.microsoft.com/security-info'


def save_config(username, password, secret):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'secret': secret}, f)
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump({'username': username, 'password': password}, f)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def load_credentials():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    with open(CREDENTIALS_FILE, 'r') as f:
        return json.load(f)


def first_time_setup():
    creds = load_credentials()
    if creds:
        username = creds['username']
        password = creds['password']
        print('Loaded existing credentials. Starting automated login and 2FA binding...')
    else:
        username = input('Enter your Microsoft username: ')
        password = input('Enter your Microsoft password: ')
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump({'username': username, 'password': password}, f)
        print('Credentials saved. Starting automated login and 2FA binding...')
    driver = start_driver()
    # Automated login
    driver.get(LOGIN_URL)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'loginfmt')))
        driver.find_element(By.NAME, 'loginfmt').send_keys(username)
        driver.find_element(By.ID, 'idSIButton9').click()
        time.sleep(2)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'passwd')))
        driver.find_element(By.NAME, 'passwd').send_keys(password)
        driver.find_element(By.ID, 'idSIButton9').click()
        time.sleep(2)
        # Continuously check and tick '不再显示此消息' checkbox, then click '是' button until navigation
        for _ in range(30):  # up to 30 seconds
            try:
                # Tick the checkbox if present and not already selected
                try:
                    kmsi_checkbox = driver.find_element(By.ID, "KmsiCheckboxField")
                    if kmsi_checkbox.is_displayed() and kmsi_checkbox.is_enabled() and not kmsi_checkbox.is_selected():
                        print("Ticking '不再显示此消息' checkbox...")
                        kmsi_checkbox.click()
                        time.sleep(0.5)
                except Exception:
                    pass
                # Find the confirmation button robustly (submit, class contains 'button_primary', value is '是')
                btn_candidates = driver.find_elements(By.CSS_SELECTOR, "input[type='submit'].button_primary")
                btn_clicked = False
                for btn in btn_candidates:
                    btn_class = btn.get_attribute('class') or ''
                    btn_value = btn.get_attribute('value') or ''
                    print(f"Found button: class={btn_class}, value={btn_value}")
                    match_values = ['是', '下一步', 'Yes', '同意', '确认', '继续', '登录', 'Sign in', 'Accept', 'Next', 'Continue']
                    if btn.is_displayed() and btn.is_enabled() and any(x in btn_value for x in match_values):
                        print(f"Attempting to click button with value '{btn_value}' ...")
                        try:
                            btn.click()
                            print(f"Clicked button '{btn_value}' with normal click.")
                        except Exception:
                            print("Normal click failed, trying JS click...")
                            driver.execute_script("arguments[0].click();", btn)
                            print(f"Clicked button '{btn_value}' with JS click.")
                        time.sleep(1)
                        btn_clicked = True
                        break
                if not btn_clicked:
                    print("No clickable main button found, waiting...")
                    time.sleep(1)
            except Exception as e:
                print(f"Exception in confirmation loop: {e}")
                break  # Button not present, stop loop
        # Wait for navigation to security info page
        print('Waiting for navigation to security info page...')
        max_wait = 60
        waited = 0
        while waited < max_wait:
            current_url = driver.current_url
            if current_url.startswith(SECURITY_INFO_URL):
                print('Successfully navigated to security info page. Automating authenticator binding...')
                break
            time.sleep(2)
            waited += 2
        else:
            print('Did not reach security info page after login. Please check credentials or login flow.')
            driver.quit()
            return
        try:
            # Step 1: Click <span> with data-automationid="splitbuttonprimary" and child <i> with data-icon-name="Add"
            icon_add = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'span[data-automationid="splitbuttonprimary"] i[data-icon-name="Add"]'))
            )
            btn1 = icon_add.find_element(By.XPATH, './..')
            btn1.click()
            time.sleep(1)
            # Step 2: Click button with data-testid="authmethod-picker-authenticatorApp"
            btn2 = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="authmethod-picker-authenticatorApp"]'))
            )
            btn2.click()
            time.sleep(1)
            # Step 3: Click button with class d_hxfHpJiF_9Hwnz7WNw
            btn3 = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'd_hxfHpJiF_9Hwnz7WNw'))
            )
            btn3.click()
            time.sleep(1)
            # Step 4: Click button with data-testid="reskin-step-next-button"
            btn4 = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="reskin-step-next-button"]'))
            )
            btn4.click()
            time.sleep(1)
            # Step 5: Click button with data-testid="activation-qr-show/hide-info-button"
            btn5 = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="activation-qr-show/hide-info-button"]'))
            )
            btn5.click()
            time.sleep(1)
            # Step 6: Extract secret from <tr> with data-testid="activation-url/key"
            secret_elem = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'tr[data-testid="activation-url/key"]'))
            )
            secret = secret_elem.text.strip()
            if secret:
                bind(secret)
                save_config(username, password, secret)
                print(f'Authenticator bound and secret saved: {secret}')
                # Click '下一步' button after copying secret
                btn_next = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="reskin-step-next-button"]'))
                )
                btn_next.click()
                time.sleep(1)
                # Step 7: Fill OTP in the input field (robust)
                otp_input = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-testid="verification-entercode-input"]'))
                )
                otp_input.clear()
                otp = get_otp()
                otp_input.send_keys(otp)
                print(f'Filled OTP: {otp}')
                # Click '下一步' button to submit OTP
                btn_otp_next = WebDriverWait(driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="reskin-step-next-button"]'))
                )
                btn_otp_next.click()
                time.sleep(1)
            else:
                print('Could not extract secret automatically. Please bind manually and update config.')
        except Exception as e:
            print(f'Error during security info automation: {e}')
        print('Automation complete. Waiting 10 seconds before exit...')
        time.sleep(10)
    except Exception as e:
        print(f'Error during automated login/setup: {e}')
    driver.quit()


def start_driver():
    options = Options()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def auto_login():
    config = load_config()
    creds = load_credentials()
    if not config or not creds or 'secret' not in config or 'username' not in creds or 'password' not in creds:
        print('Config or credentials missing/incomplete. Starting first-time setup...')
        first_time_setup()
        config = load_config()
        creds = load_credentials()
        if not config or not creds or 'secret' not in config or 'username' not in creds or 'password' not in creds:
            raise RuntimeError('Failed to create valid config or credentials file. Please retry.')
    username = creds['username']
    password = creds['password']
    secret = config.get('secret')
    driver = start_driver()
    driver.get(LOGIN_URL)
    # --- Insert element automation here ---
    # Example: fill username
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'loginfmt')))
        driver.find_element(By.NAME, 'loginfmt').send_keys(username)
        driver.find_element(By.ID, 'idSIButton9').click()
        time.sleep(2)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'passwd')))
        driver.find_element(By.NAME, 'passwd').send_keys(password)
        driver.find_element(By.ID, 'idSIButton9').click()
        time.sleep(2)
        # If OTP requested, fill it
        if 'Enter code' in driver.page_source or 'Verification code' in driver.page_source:
            otp = get_otp()
            # You will tell me the exact element for OTP input
            print(f'Auto-filling OTP: {otp}')
            # Example: driver.find_element(By.NAME, 'otc').send_keys(otp)
            # driver.find_element(By.ID, 'idSubmit_SAOTCC_Continue').click()
        print('Login automation complete. Please specify further element IDs/XPaths for full automation.')
    except Exception as e:
        print(f'Error during login automation: {e}')
    # driver.quit() # Uncomment when ready

def login_with_credentials(driver, username, password):
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'loginfmt')))
    driver.find_element(By.NAME, 'loginfmt').send_keys(username)
    driver.find_element(By.ID, 'idSIButton9').click()
    time.sleep(2)
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, 'passwd')))
    driver.find_element(By.NAME, 'passwd').send_keys(password)
    driver.find_element(By.ID, 'idSIButton9').click()
    time.sleep(2)
    # Continuously check and tick '不再显示此消息' checkbox, then click '是' button until navigation
    for _ in range(30):  # up to 30 seconds
        try:
            # Tick the checkbox if present and not already selected
            try:
                kmsi_checkbox = driver.find_element(By.ID, "KmsiCheckboxField")
                if kmsi_checkbox.is_displayed() and kmsi_checkbox.is_enabled() and not kmsi_checkbox.is_selected():
                    print("Ticking '不再显示此消息' checkbox...")
                    kmsi_checkbox.click()
                    time.sleep(0.5)
            except Exception:
                pass
            # Find the confirmation button robustly (submit, class contains 'button_primary', value is '是')
            btn_candidates = driver.find_elements(By.CSS_SELECTOR, "input[type='submit'].button_primary")
            btn_clicked = False
            for btn in btn_candidates:
                btn_class = btn.get_attribute('class') or ''
                btn_value = btn.get_attribute('value') or ''
                print(f"Found button: class={btn_class}, value={btn_value}")
                match_values = ['是', '下一步', 'Yes', '同意', '确认', '继续', '登录', 'Sign in', 'Accept', 'Next', 'Continue']
                if btn.is_displayed() and btn.is_enabled() and any(x in btn_value for x in match_values):
                    print(f"Attempting to click button with value '{btn_value}' ...")
                    try:
                        btn.click()
                        print(f"Clicked button '{btn_value}' with normal click.")
                    except Exception:
                        print("Normal click failed, trying JS click...")
                        driver.execute_script("arguments[0].click();", btn)
                        print(f"Clicked button '{btn_value}' with JS click.")
                    time.sleep(1)
                    btn_clicked = True
                    break
            if not btn_clicked:
                print("No clickable main button found, waiting...")
                time.sleep(1)
        except Exception as e:
            print(f"Exception in confirmation loop: {e}")
            break  # Button not present, stop loop

def fill_otp(driver):
    try:
        otp_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[data-testid="verification-entercode-input"]'))
        )
        otp_input.clear()
        otp = get_otp()
        otp_input.send_keys(otp)
        print(f'Filled OTP: {otp}')
        btn_otp_next = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="reskin-step-next-button"]'))
        )
        btn_otp_next.click()
        time.sleep(1)
        return True
    except Exception as e:
        print(f'OTP input not found or not needed: {e}')
        return False
    
if __name__ == '__main__':
    first_time_setup()
