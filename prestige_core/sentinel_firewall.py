"""Odwracalne reguły zapory Sentinel, ograniczone do własnej przestrzeni nazw."""

import base64
import ipaddress
import json
import os
import subprocess


PREFIX = "PrestigeTech.Sentinel.Block"


def _address(value):
    try:
        address = ipaddress.IPv4Address(value)
    except (ipaddress.AddressValueError, TypeError) as error:
        raise ValueError("Wymagany pojedynczy adres IPv4.") from error
    if (address.is_loopback or address.is_link_local or address.is_multicast
            or address.is_unspecified or address.is_reserved):
        raise ValueError("Adres specjalny nie może być blokowany.")
    if str(address) == "255.255.255.255":
        raise ValueError("Adres rozgłoszeniowy nie może być blokowany.")
    return str(address)


def rule_name(address, direction):
    if direction not in ("Inbound", "Outbound"):
        raise ValueError("Nieprawidłowy kierunek reguły.")
    return f"{PREFIX}.{_address(address)}.{direction}"


def _validate_existing(rule, address, direction):
    if rule is None:
        return
    if (rule.get("name") != rule_name(address, direction)
            or rule.get("direction") != direction or rule.get("action") != "Block"
            or rule.get("remote") != address
            or rule.get("description") != "Prestige Tech Network Sentinel"):
        raise RuntimeError("Istniejąca reguła o tej nazwie nie należy do Sentinel; nie zmieniono zapory.")


def change_block(address, backend, *, enable, apply=False):
    """Dwie reguły IN/OUT; w razie błędu cofnij zmiany tej operacji."""
    address = _address(address)
    protected = set()
    for item in backend.protected_addresses():
        try:
            protected.add(_address(item))
        except ValueError:
            continue  # IPv6 DNS nie jest celem reguły IPv4.
    if address in protected:
        raise ValueError("Nie można blokować adresu własnego komputera, bramy ani DNS.")
    directions = ("Inbound", "Outbound")
    existing = {direction: backend.get(rule_name(address, direction)) for direction in directions}
    for direction in directions:
        _validate_existing(existing[direction], address, direction)
    needed = [direction for direction in directions
              if (existing[direction] is None) == enable]
    if not apply:
        return {"status": "PLAN", "address": address, "enable": enable,
                "directions": needed}
    completed = []
    try:
        for direction in needed:
            if enable:
                backend.add(rule_name(address, direction), address, direction)
            else:
                backend.remove(rule_name(address, direction))
            completed.append(direction)
        for direction in directions:
            actual = backend.get(rule_name(address, direction))
            _validate_existing(actual, address, direction)
            if (actual is not None) != enable:
                raise RuntimeError("Weryfikacja reguł zapory nie powiodła się.")
    except Exception as error:
        rollback_errors = []
        for direction in reversed(directions):
            try:
                name = rule_name(address, direction)
                current = backend.get(name)
                _validate_existing(current, address, direction)
                if (current is None) == (existing[direction] is None):
                    continue
                if existing[direction] is None:
                    backend.remove(name)
                else:
                    backend.add(name, address, direction)
                restored = backend.get(name)
                _validate_existing(restored, address, direction)
                if (restored is None) != (existing[direction] is None):
                    raise RuntimeError("Weryfikacja cofnięcia nie powiodła się.")
            except Exception as rollback_error:
                rollback_errors.append(str(rollback_error))
        if rollback_errors:
            raise RuntimeError("Częściowa zmiana zapory; cofnięcie nieudane: "
                               + "; ".join(rollback_errors)) from error
        raise RuntimeError("Zmiana zapory nieudana; cofnięto zmiany tej operacji.") from error
    return {"status": "BLOCKED" if enable else "UNBLOCKED", "address": address,
            "changed": completed}


class WindowsFirewallBackend:
    def __init__(self, *, runner=subprocess.run):
        if os.name != "nt":
            raise RuntimeError("Zapora Sentinel wymaga Windows.")
        self.runner = runner

    def _run(self, script):
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            result = self.runner(["powershell.exe", "-NoProfile", "-NonInteractive",
                                  "-EncodedCommand", encoded], capture_output=True,
                                 text=True, encoding="utf-8", timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("Polecenie zapory nie zostało wykonane.") from error
        if result.returncode:
            detail = (result.stderr or "").strip().splitlines()
            raise RuntimeError("Polecenie zapory zakończyło się błędem: "
                               + (detail[-1][:500] if detail else "sprawdź uprawnienia administratora."))
        try:
            return json.loads((result.stdout or "null").lstrip("\ufeff"))
        except json.JSONDecodeError as error:
            raise RuntimeError("Zapora zwróciła nieprawidłową odpowiedź.") from error

    def protected_addresses(self):
        script = ("$ErrorActionPreference='Stop';"
                  "$items=@(Get-NetIPConfiguration | ForEach-Object {"
                  "@($_.IPv4Address | ForEach-Object {$_.IPAddress});"
                  "@($_.IPv4DefaultGateway | ForEach-Object {$_.NextHop});"
                  "@($_.DNSServer.ServerAddresses)});"
                  "@($items | Where-Object {$_}) | ConvertTo-Json -Compress")
        value = self._run(script)
        return value if isinstance(value, list) else ([value] if value else [])

    def get(self, name):
        script = ("$ErrorActionPreference='Stop';"
                  f"$r=Get-NetFirewallRule -Name '{name}' -ErrorAction SilentlyContinue;"
                  "if($null -eq $r){$null|ConvertTo-Json -Compress;exit 0};"
                  "$a=$r|Get-NetFirewallAddressFilter;"
                  "[ordered]@{name=$r.Name;direction=[string]$r.Direction;"
                  "action=[string]$r.Action;remote=[string]$a.RemoteAddress;"
                  "description=[string]$r.Description}|ConvertTo-Json -Compress")
        return self._run(script)

    def add(self, name, address, direction):
        script = ("$ErrorActionPreference='Stop';"
                  f"New-NetFirewallRule -Name '{name}' -DisplayName '{name}' "
                  f"-Direction {direction} -Action Block -RemoteAddress '{address}' "
                  "-Profile Any -Description 'Prestige Tech Network Sentinel' | Out-Null;"
                  "@{ok=$true}|ConvertTo-Json -Compress")
        self._run(script)

    def remove(self, name):
        script = ("$ErrorActionPreference='Stop';"
                  f"Remove-NetFirewallRule -Name '{name}' -ErrorAction Stop;"
                  "@{ok=$true}|ConvertTo-Json -Compress")
        self._run(script)
