import json
import logging
import os
from datetime import datetime

import requests

DEFAULT_TIMEOUT = 5


class DiscordBroadcaster:
    """Lightweight Discord webhook broadcaster with profile prefixing."""

    def __init__(self, credentials_path='credentials.json', logger=None, profile_name=None):
        self.logger = logger or logging.getLogger("attendance_bot")
        self.credentials_path = credentials_path
        self.webhook_url = None
        self.enabled = False
        self.profile_name = profile_name or "Unknown"
        self._load_settings()

    def _load_settings(self):
        try:
            with open(self.credentials_path, 'r') as f:
                data = json.load(f)
            self.webhook_url = data.get('discord_webhook_url')
            if not self.profile_name and data.get('profile_nickname'):
                self.profile_name = data.get('profile_nickname')
            enabled_flag = data.get('enable_discord_webhook', True)
            self.enabled = bool(self.webhook_url) and bool(enabled_flag)
        except Exception:
            self.enabled = False
            self.webhook_url = None

    def _send(self, content):
        if not self.enabled or not self.webhook_url:
            return False
        message = content
        if self.profile_name:
            message = f"[{self.profile_name}] {content}"
        try:
            resp = requests.post(self.webhook_url, json={"content": message}, timeout=DEFAULT_TIMEOUT)
            if resp.status_code >= 400:
                self.logger.warning(f"Discord webhook failed: {resp.status_code} {resp.text}")
                return False
            return True
        except Exception as e:
            self.logger.warning(f"Discord webhook error: {e}")
            return False

    def notify_bot_started(self, version_label=None):
        suffix = f" ({version_label})" if version_label else ""
        return self._send(f"🚀 Bot started{suffix}")

    def notify_bot_stopped(self, runtime=None):
        suffix = f" (runtime {runtime})" if runtime else ""
        return self._send(f"🛑 Bot stopped{suffix}")

    def notify_renew_login_success(self):
        return self._send("✅ renew_login succeeded")

    def notify_attendance_success(self, event_name, event_time=None):
        when = ""
        if isinstance(event_time, datetime):
            try:
                local_time = event_time.astimezone()
                when = f" at {local_time.strftime('%Y-%m-%d %H:%M:%S')}"
            except Exception:
                pass
        return self._send(f"✅ Attendance marked: {event_name}{when}")
