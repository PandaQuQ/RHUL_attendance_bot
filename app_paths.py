import os

APP_DIR_NAME = ".rhul_attendance_bot"
PROFILES_DIR_NAME = "profiles"


def get_app_dir():
    app_dir = os.path.join(os.path.expanduser("~"), APP_DIR_NAME)
    os.makedirs(app_dir, exist_ok=True)
    return app_dir


def _normalize_profile(profile_name=None):
    name = (profile_name or "default").strip() or "default"
    name = name.replace(os.sep, "_")
    if os.altsep:
        name = name.replace(os.altsep, "_")
    return name


def get_profile_dir(profile_name=None):
    base = os.path.join(get_app_dir(), PROFILES_DIR_NAME)
    os.makedirs(base, exist_ok=True)
    profile_dir = os.path.join(base, _normalize_profile(profile_name))
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir


def profile_exists(profile_name):
    base = os.path.join(get_app_dir(), PROFILES_DIR_NAME)
    name = _normalize_profile(profile_name)
    return os.path.isdir(os.path.join(base, name))


def rename_profile(old_name, new_name):
    old_norm = _normalize_profile(old_name)
    new_norm = _normalize_profile(new_name)
    if old_norm == new_norm:
        return True
    base = os.path.join(get_app_dir(), PROFILES_DIR_NAME)
    old_path = os.path.join(base, old_norm)
    new_path = os.path.join(base, new_norm)
    if not os.path.isdir(old_path):
        return False
    if os.path.exists(new_path):
        return False
    os.makedirs(base, exist_ok=True)
    try:
        os.rename(old_path, new_path)
        return True
    except Exception:
        return False


def list_profiles():
    base = os.path.join(get_app_dir(), PROFILES_DIR_NAME)
    if not os.path.isdir(base):
        return []
    profiles = [name for name in os.listdir(base) if os.path.isdir(os.path.join(base, name))]
    profiles.sort()
    return profiles


def prompt_select_profile():
    profiles = list_profiles()
    if not profiles:
        return "default"

    print("Select a profile:")
    for idx, name in enumerate(profiles, start=1):
        print(f"  {idx}. {name}")
    while True:
        choice = input("Enter number or type a new profile name: ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(profiles):
                return profiles[idx - 1]
        elif choice:
            return _normalize_profile(choice)
        print("Invalid selection. Please try again.")


def get_credentials_path(profile_name=None):
    return os.path.join(get_profile_dir(profile_name), "credentials.json")


def get_2fa_config_path(profile_name=None):
    return os.path.join(get_profile_dir(profile_name), "2fa_config.json")


def get_ics_dir(profile_name=None):
    ics_dir = os.path.join(get_profile_dir(profile_name), "ics")
    os.makedirs(ics_dir, exist_ok=True)
    return ics_dir


def get_chrome_user_data_dir(profile_name=None):
    user_dir = os.path.join(get_profile_dir(profile_name), "chrome_user_data")
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def delete_app_data():
    app_dir = get_app_dir()
    if not os.path.isdir(app_dir):
        return False
    for root, dirs, files in os.walk(app_dir, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except Exception:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except Exception:
                pass
    try:
        os.rmdir(app_dir)
    except Exception:
        pass
    return True
