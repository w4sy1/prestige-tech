"""Kontrolowana zmiana MTU IPv4 z kopią i warunkowym przywróceniem."""

import ipaddress
import json
from pathlib import Path
import uuid

from .internet_diagnostic import mtu_probe
from .network_dns_change import WindowsDnsBackend, _index, _save_new, _update


def _mtu(value):
    if type(value) is not int or not 576 <= value <= 1500:
        raise ValueError("MTU do kontrolowanej zmiany musi mieścić się w zakresie 576–1500.")
    return value


def _target(value):
    address = ipaddress.IPv4Address(value)
    if address.is_loopback or address.is_multicast or address.is_unspecified:
        raise ValueError("Wybierz osiągalny IPv4 do sondy DF.")
    return str(address)


def _state(row):
    if not isinstance(row, dict) or type(row.get("index")) is not int:
        raise RuntimeError("Niepełny odczyt MTU.")
    return {"index": _index(row["index"]), "mtu": _mtu(row.get("mtu"))}


def plan_mtu_change(index, value, probe_target, backend):
    index, value, probe_target = _index(index), _mtu(value), _target(probe_target)
    original = _state(backend.snapshot_mtu(index))
    if original["index"] != index:
        raise RuntimeError("System zwrócił inny interfejs niż wybrany.")
    return {"original": original, "desired": {"index": index, "mtu": value},
            "probe_target": probe_target, "change_needed": original["mtu"] != value,
            "probe_note": "ICMP DF używa routingu systemowego; nie potwierdza użycia wybranego adaptera."}


def apply_mtu_change(index, value, probe_target, backup_path, backend, *, probe=mtu_probe):
    plan = plan_mtu_change(index, value, probe_target, backend)
    if not plan["change_needed"]:
        return {"status": "UNCHANGED", **plan}
    backup = Path(backup_path)
    if backup.exists() or not backup.parent.is_dir():
        raise FileExistsError("Kopia musi być nowym plikiem w istniejącym katalogu.")
    before = probe(plan["probe_target"])
    if before.get("status") != "ESTIMATE":
        raise RuntimeError("Brak wiarygodnej odpowiedzi sondy DF przed zmianą; MTU nie zmieniono.")
    record = {"schema_version": 1, "operation": "network-mtu-ipv4", "id": uuid.uuid4().hex,
              **plan, "before_probe": before, "status": "PREPARED"}
    _save_new(backup, record)
    try:
        backend.set_mtu(index, value)
        current = _state(backend.snapshot_mtu(index))
        if current != plan["desired"]:
            raise RuntimeError("Zmiana MTU nie została potwierdzona odczytem.")
        after = probe(plan["probe_target"])
        record["after_probe"] = after
        if after.get("status") != "ESTIMATE":
            raise RuntimeError("Brak odpowiedzi sondy DF po zmianie.")
    except Exception as error:
        record["status"] = "RECOVERY_NEEDED"
        try:
            current = _state(backend.snapshot_mtu(index))
            if current == plan["desired"]:
                backend.set_mtu(index, plan["original"]["mtu"])
                if _state(backend.snapshot_mtu(index)) == plan["original"]:
                    record["status"] = "ROLLED_BACK_AFTER_ERROR"
        except Exception:
            pass
        _update(backup, record)
        raise RuntimeError(f"Zmiana MTU nieudana; stan kopii: {record['status']}.") from error
    record["status"] = "APPLIED"
    record["recommend_rollback"] = after["estimated_ipv4_mtu"] < before["estimated_ipv4_mtu"]
    _update(backup, record)
    return {"status": "APPLIED", "backup": str(backup.resolve()),
            "before_probe": before, "after_probe": after,
            "recommend_rollback": record["recommend_rollback"], **plan}


def rollback_mtu_change(backup_path, backend, *, apply=False):
    record = json.loads(Path(backup_path).read_text(encoding="utf-8"))
    if (not isinstance(record, dict) or record.get("schema_version") != 1
            or record.get("operation") != "network-mtu-ipv4"
            or record.get("status") not in ("APPLIED", "PREPARED", "RECOVERY_NEEDED")):
        raise ValueError("Kopia MTU nie opisuje zmiany możliwej do cofnięcia.")
    original, desired = _state(record["original"]), _state(record["desired"])
    if original["index"] != desired["index"]:
        raise ValueError("Kopia MTU wskazuje różne interfejsy.")
    current = _state(backend.snapshot_mtu(original["index"]))
    if current == original:
        return {"status": "ALREADY_RESTORED"}
    if current != desired:
        raise RuntimeError("MTU zmieniono od czasu kopii; automatyczne cofnięcie odmówione.")
    if not apply:
        return {"status": "PLAN", "backup_status": record["status"],
                "current": current, "restore": original}
    backend.set_mtu(original["index"], original["mtu"])
    if _state(backend.snapshot_mtu(original["index"])) != original:
        raise RuntimeError("Nie potwierdzono przywrócenia MTU.")
    record["status"] = "ROLLED_BACK"
    _update(backup_path, record)
    return {"status": "ROLLED_BACK", "restored": original}


class WindowsMtuBackend(WindowsDnsBackend):
    def snapshot_mtu(self, index):
        index = _index(index)
        script = ("$ErrorActionPreference='Stop';"
                  f"$r=Get-NetIPInterface -InterfaceIndex {index} -AddressFamily IPv4 -ErrorAction Stop;"
                  f"[pscustomobject]@{{index={index};mtu=[int]$r.NlMtu}}|ConvertTo-Json -Compress")
        return self._run(script)

    def set_mtu(self, index, value):
        index, value = _index(index), _mtu(value)
        script = ("$ErrorActionPreference='Stop';"
                  f"Set-NetIPInterface -InterfaceIndex {index} -AddressFamily IPv4 "
                  f"-NlMtuBytes {value} -ErrorAction Stop;"
                  "@{ok=$true}|ConvertTo-Json -Compress")
        self._run(script)
