"""Zmiana DNS IPv4 z nową kopią, weryfikacją i warunkowym cofnięciem."""

import base64
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import uuid


def _index(value):
    if type(value) is not int or not 1 <= value <= 65535:
        raise ValueError("Nieprawidłowy indeks interfejsu.")
    return value


def _servers(values):
    if values is None:
        return None
    if not isinstance(values, (list, tuple)) or not 1 <= len(values) <= 4:
        raise ValueError("Podaj 1–4 adresy serwerów DNS IPv4 albo tryb automatyczny.")
    normalized = []
    for value in values:
        address = str(ipaddress.IPv4Address(value))
        if address == "0.0.0.0" or address == "255.255.255.255" or address in normalized:
            raise ValueError("Nieprawidłowy lub powtórzony serwer DNS.")
        normalized.append(address)
    return normalized


def _state(row):
    if (not isinstance(row, dict) or type(row.get("index")) is not int
            or type(row.get("automatic")) is not bool
            or not isinstance(row.get("servers"), list)):
        raise RuntimeError("Niepełny odczyt konfiguracji DNS.")
    return {"index": _index(row["index"]), "automatic": row["automatic"],
            "servers": [str(ipaddress.IPv4Address(value)) for value in row["servers"]]}


def _save_new(path, record):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _update(path, record):
    path = Path(path)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        _save_new(temporary, record)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _same(left, right):
    if left["automatic"] != right["automatic"]:
        return False
    return left["automatic"] or left["servers"] == right["servers"]


def plan_dns_change(index, servers, backend):
    return _plan_dns_change(index, servers, backend, _servers, _state)


def _plan_dns_change(index, servers, backend, validate_servers, validate_state):
    index = _index(index)
    desired_servers = validate_servers(servers)
    original = validate_state(backend.snapshot(index))
    if original["index"] != index:
        raise RuntimeError("System zwrócił inny interfejs niż wybrany.")
    desired = {"index": index, "automatic": desired_servers is None,
               "servers": desired_servers if desired_servers is not None else []}
    return {"original": original, "desired": desired,
            "change_needed": not _same(original, desired)}


def apply_dns_change(index, servers, backup_path, backend):
    return _apply_dns_change(index, servers, backup_path, backend,
                             _servers, _state, "network-dns-ipv4")


def _apply_dns_change(index, servers, backup_path, backend, validate_servers,
                      validate_state, operation):
    plan = _plan_dns_change(index, servers, backend, validate_servers, validate_state)
    if not plan["change_needed"]:
        return {"status": "UNCHANGED", **plan}
    backup = Path(backup_path)
    if backup.exists() or not backup.parent.is_dir():
        raise FileExistsError("Kopia musi być nowym plikiem w istniejącym katalogu.")
    record = {"schema_version": 1, "operation": operation,
              "id": uuid.uuid4().hex, "created_utc": datetime.now(timezone.utc).isoformat(),
              **plan, "status": "PREPARED"}
    _save_new(backup, record)
    try:
        backend.set_dns(index, plan["desired"]["servers"] if not plan["desired"]["automatic"] else None)
        current = validate_state(backend.snapshot(index))
        if not _same(current, plan["desired"]):
            raise RuntimeError("Zmiana DNS nie została potwierdzona odczytem.")
    except Exception as error:
        record["status"] = "RECOVERY_NEEDED"
        try:
            current = validate_state(backend.snapshot(index))
            if _same(current, plan["desired"]):
                backend.set_dns(index, None if plan["original"]["automatic"] else plan["original"]["servers"])
                if _same(validate_state(backend.snapshot(index)), plan["original"]):
                    record["status"] = "ROLLED_BACK_AFTER_ERROR"
        except Exception:
            pass
        _update(backup, record)
        raise RuntimeError(f"Zmiana DNS nieudana; stan kopii: {record['status']}.") from error
    record["status"] = "APPLIED"
    _update(backup, record)
    return {"status": "APPLIED", "backup": str(backup.resolve()), **plan}


def rollback_dns_change(backup_path, backend, *, apply=False):
    return _rollback_dns_change(backup_path, backend, apply=apply,
                                state=_state, operation="network-dns-ipv4")


def _rollback_dns_change(backup_path, backend, *, apply, state, operation):
    record = json.loads(Path(backup_path).read_text(encoding="utf-8"))
    if (not isinstance(record, dict) or record.get("schema_version") != 1
            or record.get("operation") != operation
            or record.get("status") not in ("APPLIED", "PREPARED", "RECOVERY_NEEDED")):
        raise ValueError("Kopia DNS nie opisuje zmiany możliwej do cofnięcia.")
    original, desired = state(record["original"]), state(record["desired"])
    if original["index"] != desired["index"]:
        raise ValueError("Kopia DNS wskazuje różne interfejsy.")
    current = state(backend.snapshot(original["index"]))
    if _same(current, original):
        return {"status": "ALREADY_RESTORED"}
    if not _same(current, desired):
        raise RuntimeError("DNS zmieniono od czasu kopii; automatyczne cofnięcie odmówione.")
    if not apply:
        return {"status": "PLAN", "backup_status": record["status"],
                "current": current, "restore": original}
    backend.set_dns(original["index"], None if original["automatic"] else original["servers"])
    if not _same(state(backend.snapshot(original["index"])), original):
        raise RuntimeError("Nie potwierdzono przywrócenia DNS.")
    record["status"] = "ROLLED_BACK"
    _update(backup_path, record)
    return {"status": "ROLLED_BACK", "restored": original}


class WindowsDnsBackend:
    def __init__(self, *, runner=subprocess.run):
        if os.name != "nt":
            raise RuntimeError("Zmiana DNS wymaga Windows.")
        self.runner = runner

    def _run(self, script):
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        try:
            result = self.runner(["powershell.exe", "-NoProfile", "-NonInteractive",
                                  "-EncodedCommand", encoded], capture_output=True, text=True,
                                 encoding="utf-8", timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("Polecenie DNS nie zostało wykonane.") from error
        if result.returncode:
            raise RuntimeError("Polecenie DNS zakończyło się błędem; sprawdź uprawnienia administratora.")
        try:
            return json.loads((result.stdout or "").lstrip("\ufeff"))
        except json.JSONDecodeError as error:
            raise RuntimeError("Polecenie DNS zwróciło nieprawidłowy wynik.") from error

    def snapshot(self, index):
        index = _index(index)
        script = ("[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"
                  "$ErrorActionPreference='Stop';"
                  f"$a=Get-NetAdapter -InterfaceIndex {index} -ErrorAction Stop;"
                  "$key='HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters\\Interfaces\\'+$a.InterfaceGuid;"
                  "$p=Get-ItemProperty -LiteralPath $key -ErrorAction Stop;"
                  f"$d=Get-DnsClientServerAddress -InterfaceIndex {index} -AddressFamily IPv4 -ErrorAction Stop;"
                  f"[pscustomobject]@{{index={index};automatic=[string]::IsNullOrWhiteSpace($p.NameServer);"
                  "servers=@($d.ServerAddresses)}|ConvertTo-Json -Depth 4 -Compress")
        return self._run(script)

    def set_dns(self, index, servers):
        index = _index(index)
        servers = _servers(servers)
        if servers is None:
            command = f"Set-DnsClientServerAddress -InterfaceIndex {index} -ResetServerAddresses -ErrorAction Stop"
        else:
            quoted = ",".join("'" + address + "'" for address in servers)
            command = f"Set-DnsClientServerAddress -InterfaceIndex {index} -ServerAddresses @({quoted}) -ErrorAction Stop"
        self._run("$ErrorActionPreference='Stop';" + command + ";@{ok=$true}|ConvertTo-Json -Compress")
