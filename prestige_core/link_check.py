"""Lokalna analiza widocznych cech adresu; bez otwierania strony."""

import ipaddress
from urllib.parse import urlsplit


def inspect_link(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError("Wpisz adres strony (maksymalnie 4096 znaków).")
    raw = value.strip()
    if any(ord(char) < 32 for char in raw) or "\\" in raw:
        raise ValueError("Adres zawiera niedozwolone znaki.")
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parsed = urlsplit(raw)
        host = (parsed.hostname or "").rstrip(".").lower()
        port = parsed.port
    except ValueError as error:
        raise ValueError("Nieprawidłowy adres strony.") from error
    if parsed.scheme.lower() not in ("http", "https") or not host or not parsed.netloc:
        raise ValueError("Podaj adres strony HTTP lub HTTPS.")
    if len(host) > 253 or any(len(part) > 63 or not part for part in host.split(".")):
        raise ValueError("Nieprawidłowa nazwa strony.")
    findings = []
    if parsed.username is not None or parsed.password is not None:
        findings.append("Adres zawiera znak @; prawdziwa domena jest po jego prawej stronie.")
    if parsed.scheme.lower() == "http":
        findings.append("Połączenie HTTP nie szyfruje przesyłanych danych.")
    if any(ord(char) > 127 for char in host) or "xn--" in host:
        findings.append("Nazwa zawiera znaki międzynarodowe; sprawdź ją uważnie.")
    try:
        ipaddress.ip_address(host)
        findings.append("Zamiast nazwy domeny podano adres IP.")
    except ValueError:
        pass
    if port not in (None, 80, 443):
        findings.append("Adres używa nietypowego portu.")
    if host.count(".") >= 4:
        findings.append("Nazwa ma wiele części; sprawdź właściwą domenę.")
    return {"status": "REVIEW" if findings else "UNKNOWN", "domain": host,
            "findings": findings, "opened_page": False, "sent_to_network": False,
            "message": ("Sprawdź adres przed wpisaniem danych." if findings else
                        "Nie znaleziono prostych sygnałów ostrzegawczych. To nie potwierdza, że strona jest bezpieczna.")}
