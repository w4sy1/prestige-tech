"""Jawne zapytanie VirusTotal o SHA-256; nigdy nie wysyła pliku."""

import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://www.virustotal.com/api/v3/files/"
MAX_FILE_BYTES = 2 * 1024 * 1024 * 1024


def hash_file(path):
    source = Path(path)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Wymagany zwykły plik do 2 GiB.")
    digest = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def lookup_hash(sha256, *, api_key=None, opener=urlopen):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", sha256 or ""):
        raise ValueError("Wymagany SHA-256.")
    key = api_key or os.environ.get("VT_API_KEY")
    if not key:
        raise ValueError("Ustaw VT_API_KEY w środowisku; klucza nie zapisujemy w projekcie.")
    request = Request(API_URL + sha256.lower(), headers={"x-apikey": key,
                                                          "Accept": "application/json"},
                      method="GET")
    try:
        with opener(request, timeout=15) as response:
            payload = response.read(1024 * 1024 + 1)
    except HTTPError as error:
        if error.code == 404:
            return {"status": "NOT_FOUND", "sha256": sha256.lower(),
                    "note": "Brak raportu nie oznacza, że plik jest bezpieczny. Nie wysłano pliku."}
        if error.code == 429:
            raise RuntimeError("Limit zapytań VirusTotal; spróbuj później.") from error
        raise RuntimeError(f"VirusTotal nie zwrócił raportu (HTTP {error.code}).") from error
    except (URLError, TimeoutError, OSError) as error:
        raise RuntimeError("Nie udało się połączyć z VirusTotal.") from error
    if len(payload) > 1024 * 1024:
        raise RuntimeError("Raport VirusTotal przekracza limit.")
    try:
        attributes = json.loads(payload)["data"]["attributes"]
        stats = attributes["last_analysis_stats"]
        counts = {key: int(stats.get(key, 0)) for key in
                  ("malicious", "suspicious", "harmless", "undetected")}
        if any(value < 0 for value in counts.values()):
            raise ValueError
    except (ValueError, KeyError, TypeError, UnicodeError) as error:
        raise RuntimeError("Nieprawidłowy raport VirusTotal.") from error
    return {"status": "FOUND", "sha256": sha256.lower(), "counts": counts,
            "note": "Wysłano wyłącznie SHA-256. Wynik silników wymaga interpretacji; zero wykryć nie gwarantuje bezpieczeństwa."}


def lookup_file(path, *, api_key=None, opener=urlopen):
    return lookup_hash(hash_file(path), api_key=api_key, opener=opener)
