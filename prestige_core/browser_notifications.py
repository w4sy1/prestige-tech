"""Odczyt zezwoleń na powiadomienia Chrome i Edge bez modyfikacji profili."""

import json
import os
from pathlib import Path
from urllib.parse import urlsplit


MAX_PREFERENCES_BYTES = 24 * 1024 * 1024
BROWSERS = {"Chrome": ("Google", "Chrome"), "Edge": ("Microsoft", "Edge")}


def _allowed_site(origin):
    candidate = origin.split(",", 1)[0]
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        return parsed.hostname.lower()
    except ValueError:
        return None


def read_preferences(path, *, browser, profile):
    source = Path(path)
    with source.open("rb") as stream:
        raw = stream.read(MAX_PREFERENCES_BYTES + 1)
    if len(raw) > MAX_PREFERENCES_BYTES:
        raise ValueError("Profil przeglądarki jest zbyt duży do bezpiecznego odczytu.")
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("Nieprawidłowy format profilu przeglądarki.")
    profile_data = data.get("profile", {})
    if not isinstance(profile_data, dict):
        raise ValueError("Nieprawidłowy profil przeglądarki.")
    settings = profile_data.get("content_settings", {})
    if not isinstance(settings, dict) or not isinstance(settings.get("exceptions", {}), dict):
        raise ValueError("Nieprawidłowe ustawienia przeglądarki.")
    entries = settings.get("exceptions", {}).get("notifications", {})
    if not isinstance(entries, dict):
        raise ValueError("Nieprawidłowy format ustawień powiadomień.")
    rows = []
    for origin, item in entries.items():
        if not isinstance(origin, str) or not isinstance(item, dict):
            continue
        if item.get("setting") != 1:
            continue
        domain = _allowed_site(origin)
        if domain:
            rows.append({"browser": browser, "profile": profile, "domain": domain,
                         "permission": "ALLOW"})
    return rows


def collect_notification_permissions(*, local_app_data=None):
    root = Path(local_app_data or os.environ.get("LOCALAPPDATA") or Path.home())
    allowed = []
    profiles_read = 0
    errors = 0
    for browser, parts in BROWSERS.items():
        user_data = root.joinpath(*parts, "User Data")
        if not user_data.is_dir():
            continue
        profiles = [user_data / "Default", *sorted(user_data.glob("Profile [0-9]*"))[:11]]
        for profile in profiles:
            source = profile / "Preferences"
            if not source.is_file():
                continue
            try:
                allowed.extend(read_preferences(source, browser=browser, profile=profile.name))
                profiles_read += 1
            except (OSError, ValueError, UnicodeError, json.JSONDecodeError):
                errors += 1
    return {"status": "COMPLETE" if profiles_read and not errors else "PARTIAL" if profiles_read else "UNKNOWN",
            "profiles_read": profiles_read, "errors": errors,
            "allowed_sites": sorted(allowed, key=lambda row: (row["browser"], row["profile"], row["domain"])),
            "system_changed": False,
            "note": "Odczyt lokalnych ustawień. Uprawnienia zmień w przeglądarce; wynik może być nieaktualny, jeśli jest otwarta."}
