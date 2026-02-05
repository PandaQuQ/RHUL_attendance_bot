import pyotp
import json
import os
from datetime import datetime
from app_paths import get_2fa_config_path


def _resolve_config_path(profile_name=None, config_path=None):
    if config_path:
        return config_path
    return get_2fa_config_path(profile_name)


def bind(secret: str, profile_name=None, config_path=None):
    """Bind the Microsoft Authenticator secret (Base32 string)."""
    path = _resolve_config_path(profile_name, config_path)
    with open(path, 'w') as f:
        json.dump({'secret': secret}, f)


def load_secret(profile_name=None, config_path=None):
    path = _resolve_config_path(profile_name, config_path)
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f).get('secret')


def get_otp(profile_name=None, config_path=None):
    """Return the current OTP for the bound secret."""
    secret = load_secret(profile_name, config_path)
    if not secret:
        raise ValueError('No secret bound. Please bind first.')
    totp = pyotp.TOTP(secret)
    return totp.now()

# Example usage:
# bind('YOUR_BASE32_SECRET')
# print(get_otp())
