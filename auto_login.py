

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


def save_config(username, password, secret, profile_nickname=None):
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'secret': secret}, f)
    with open(CREDENTIALS_FILE, 'w') as f:
        payload = {'username': username, 'password': password}
        if profile_nickname:
            payload['profile_nickname'] = profile_nickname
        json.dump(payload, f)


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


def click_by_xpath_contains_text(driver, text, timeout=10):
    xpath = f"//*[self::button or self::a or self::div or self::span][contains(normalize-space(.), '{text}') ]"
    try:
        elem = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
        driver.execute_script("arguments[0].click();", elem)
        print(f"Clicked element with text contains: {text}")
        return True
    except Exception:
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


def click_with_retries(driver, candidates, attempts=6, delay=1.0):
    """Try multiple selectors, with normal then JS click, retrying for dynamic UI."""
    for attempt in range(1, attempts + 1):
        for by, sel, label in candidates:
            try:
                elems = driver.find_elements(by, sel)
                print(f"[click attempt {attempt}] selector={sel} label={label} found={len(elems)}")
                for elem in elems:
                    if not elem.is_displayed() or not elem.is_enabled():
                        continue
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                    try:
                        elem.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", elem)
                    print(f"[click attempt {attempt}] clicked {label} via {sel}")
                    return True
            except Exception as e:
                print(f"[click attempt {attempt}] selector={sel} error={e}")
                continue
        time.sleep(delay)
    print("click_with_retries exhausted without a click")
    return False


def first_time_setup():
    creds = load_credentials()
    profile_nickname = None
    if creds:
        username = creds.get('username')
        password = creds.get('password')
        profile_nickname = creds.get('profile_nickname')
        print('Loaded existing credentials. Starting automated login and 2FA binding...')
    else:
        username = input('Enter your Microsoft username: ')
        password = input('Enter your Microsoft password: ')
    if not profile_nickname:
        while True:
            profile_nickname = input('Enter your profile nickname: ').strip()
            if profile_nickname:
                break
            print('Profile nickname cannot be empty. Please enter again.')

    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump({'username': username, 'password': password, 'profile_nickname': profile_nickname}, f)
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
            # On first login, handle the "Don't show this again" prompt (KMSI) while user completes MFA on phone
            try:
                if driver.find_elements(By.ID, "KmsiCheckboxField"):
                    handle_kmsi(driver)
            except Exception:
                pass
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
                save_config(username, password, secret, profile_nickname)
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


def fill_ms_login(driver, username, password):
    """Robust fill for Microsoft login page (prefers password-first)."""
    try:
        click_by_xpath_contains_text(driver, 'Accept', timeout=2)  # cookie banner if any
        maybe_switch_to_login_iframe(driver)

        # Account picker
        candidates = [username, username.split('@')[0], 'Use another account', 'Other account']
        for text in candidates:
            if click_by_xpath_contains_text(driver, text, timeout=3):
                break

        def visible_el(by, sel, wait=8):
            try:
                el = WebDriverWait(driver, wait).until(EC.presence_of_element_located((by, sel)))
                if el.is_displayed():
                    return el
            except Exception:
                return None
            return None

        pwd_input = visible_el(By.ID, 'i0118') or visible_el(By.NAME, 'passwd')

        user_input = None
        for by, sel in [(By.NAME, 'loginfmt'), (By.ID, 'i0116')]:
            el = visible_el(by, sel)
            if el:
                user_input = el
                break

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

        print("Password input not found or not interactable.")
        return False
    except Exception as e:
        print(f"MS login fill failed: {e}")
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
            print("Clicked 'signInAnotherWay' link")
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
            (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs .table-row", "tile row"),
            (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs .table-row .table-cell.text-left.content", "tile content cell"),
            (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(@class,'table-row')]//div[contains(@class,'text-left')]/div[contains(normalize-space(.), 'Use a verification code')]/ancestor::div[contains(@class,'table-row')][1]", "table-row ancestor of text"),
            (By.XPATH, "//img[contains(@src,'picker_verify_code')]/ancestor::div[contains(@class,'table-row')][1]", "verify-code image row"),
            (By.CSS_SELECTOR, "img[src*='picker_verify_code']", "verify-code img"),
            (By.CSS_SELECTOR, "#idDiv_SAOTCS_Proofs", "proofs container"),
            (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(normalize-space(.), 'Use a verification code')]/parent::*", "text parent"),
            (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(normalize-space(.), 'Use a verification code')]/parent::div/parent::div", "text grandparent"),
            (By.XPATH, "//*[@id='idDiv_SAOTCS_Proofs']//div[contains(@class,'table-cell')][.//div[contains(normalize-space(.), 'Use a verification code')]]", "cell containing text"),
        ]

        otp_input = None
        for _ in range(2):
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
                    print("Clicked ancestor container for 'Use a verification code'")
                    chosen = True
                except Exception:
                    pass

            if not chosen:
                print("Could not select 'Use a verification code'.")
                return False

            print("Waiting for OTP input after clicking verification code option...")
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
                print("OTP input still not visible; retrying click on verification code option...")

        if not otp_input:
            print("OTP input not found after clicking verification code option.")
            return False

        otp_input.clear()
        otp = get_otp()
        otp_input.send_keys(otp)
        print(f"Filled OTP: {otp}")

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
            print("Verify button not found.")
            return False
        time.sleep(2)
        return True
    except Exception as e:
        print(f"MFA fallback failed: {e}")
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
            print("Ticked KMSI checkbox")
            time.sleep(0.3)
    except Exception:
        pass

    candidates = [
        (By.ID, 'idSIButton9', 'idSIButton9'),
        (By.CSS_SELECTOR, "input[type='submit'].button_primary", "button_primary submit"),
        (By.XPATH, "//input[@type='submit' and (contains(@value,'Yes') or contains(@value,'是') or contains(@value,'继续') or contains(@value,'Next') or contains(@value,'Sign in'))]", "submit value match"),
        (By.XPATH, "//button[contains(normalize-space(.), 'Yes') or contains(normalize-space(.), '是') or contains(normalize-space(.), '继续') or contains(normalize-space(.), 'Next') or contains(normalize-space(.), 'Sign in') or contains(normalize-space(.), 'Accept') or contains(normalize-space(.), '登录') or contains(normalize-space(.), '同意')]", "button text match"),
    ]
    if click_with_retries(driver, candidates, attempts=5, delay=0.6):
        print("Clicked KMSI confirmation button")
        return True
    if click_by_xpath_contains_text(driver, 'Yes', timeout=3) or click_by_xpath_contains_text(driver, 'Next', timeout=3):
        print("Clicked KMSI confirmation via text fallback")
        return True
    print("KMSI confirmation button not found")
    return False


def renew_login(driver, expected_url=None):
    """Non-first login: fill credentials, handle MFA, KMSI."""
    creds = load_credentials()
    if not creds or 'username' not in creds or 'password' not in creds:
        print('credentials.json missing username/password; cannot auto-login.')
        return False
    username = creds['username']
    password = creds['password']

    try:
        current_url = driver.current_url
        page_src = driver.page_source
        if ('login.microsoftonline.com' in current_url) or ('mysignins.microsoft.com' in current_url) or ('loginfmt' in page_src):
            print("Detected Microsoft login page; attempting auto login...")
            fill_ms_login(driver, username, password)
            handle_mfa_code(driver)
            handle_kmsi(driver)
        else:
            print("No Microsoft login page detected; skipping renew_login.")
            return True

        if expected_url:
            try:
                WebDriverWait(driver, 60).until(EC.url_contains(expected_url))
                print("Login detected via URL match.")
                return True
            except Exception:
                print("Login not detected within timeout.")
                return False
        return True
    except Exception as e:
        print(f"renew_login failed: {e}")
        return False
    
if __name__ == '__main__':
    first_time_setup()
