"""Ostrożna polityka automatycznej ochrony dla alertów Deep Capture."""

import ipaddress
from prestige_core.sentinel_firewall import _address


class ProtectionPolicy:
    """Żąda blokady dopiero po dwóch niezależnych alertach HIGH z jednego IPv4."""

    def __init__(self, *, trusted=(), local=(), max_blocks=5):
        self.trusted = {str(ipaddress.IPv4Address(ip)) for ip in trusted}
        self.local = {str(ipaddress.IPv4Address(ip)) for ip in local}
        self.max_blocks = max_blocks
        self.first = {}
        self.blocks = set()

    def consider(self, alert):
        if alert.get("severity") != "HIGH":
            return {"status": "IGNORE", "reason": "Wymagany alert HIGH."}
        try:
            address = ipaddress.IPv4Address(alert["source"])
            epoch = float(alert["epoch"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Nieprawidłowy alert ochrony.") from error
        ip = str(address)
        try:
            _address(ip)
        except ValueError:
            return {"status": "IGNORE", "reason": "Adres specjalny."}
        if ip in self.local or ip in self.trusted:
            return {"status": "IGNORE", "reason": "Adres chroniony lub specjalny."}
        if ip in self.blocks:
            return {"status": "IGNORE", "reason": "Blokada już zaplanowana."}
        first = self.first.get(ip)
        if first is None or epoch - first > 300 or epoch <= first:
            self.first[ip] = epoch
            return {"status": "OBSERVE", "address": ip, "reason": "Oczekiwanie na drugi alert HIGH."}
        if epoch - first < 20:
            return {"status": "OBSERVE", "address": ip, "reason": "Alerty nie są niezależne czasowo."}
        if len(self.blocks) >= self.max_blocks:
            return {"status": "LIMIT", "reason": "Osiągnięto limit automatycznych blokad."}
        self.blocks.add(ip)
        return {"status": "BLOCK", "address": ip, "reason": "Dwa alerty HIGH w ciągu 5 minut."}

    def release(self, address):
        """Po błędzie wykonania pozwól na ponowną decyzję dopiero po nowej parze alertów."""
        self.blocks.discard(address)
        self.first.pop(address, None)
