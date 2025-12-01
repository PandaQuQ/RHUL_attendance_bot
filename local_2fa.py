import pyotp
import json
import os
from datetime import datetime

CONFIG_FILE = '2fa_config.json'

def bind(secret: str):
    """Bind the Microsoft Authenticator secret (Base32 string)."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({'secret': secret}, f)


def load_secret():
    if not os.path.exists(CONFIG_FILE):
        return None
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f).get('secret')


def get_otp():
    """Return the current OTP for the bound secret."""
    secret = load_secret()
    if not secret:
        raise ValueError('No secret bound. Please bind first.')
    totp = pyotp.TOTP(secret)
    return totp.now()

# Example usage:
# bind('YOUR_BASE32_SECRET')
# print(get_otp())
