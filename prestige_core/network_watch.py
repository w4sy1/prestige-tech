"""Jawny, odczytowy monitoring własnej podsieci między uruchomieniami GUI."""

import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import uuid

from .network_discovery import local_scopes, plan_targets, scan_local_scope


def default_directory():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("Brak LOCALAPPDATA; wskaż katalog monitoringu.")
    return Path(base) / "PrestigeTech" / "NetworkWatch"


def _read(path, *, limit=2 * 1024 * 1024):
    source = Path(path)
    if source.is_symlink():
        raise ValueError("Nie odczytuję dowiązania symbolicznego.")
    with source.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Plik monitoringu jest zbyt duży.")
    return json.loads(data.decode("utf-8-sig"))


def _save(path, data):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError("Nie zapisuję przez dowiązanie symboliczne.")
    temporary = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def make_profile(scope, local_ip, interface_index):
    plan_targets(scope, local_ip)
    network = ipaddress.IPv4Network(scope, strict=True)
    if not 1 <= int(interface_index) <= 1000000:
        raise ValueError("Nieprawidłowy indeks adaptera.")
    return {"schema_version": 1, "scope": str(network),
            "local_ip": str(ipaddress.IPv4Address(local_ip)),
            "interface_index": int(interface_index), "scan_type": "ICMP",
            "automatic_blocking": False}


def save_profile(profile, directory):
    expected = make_profile(profile["scope"], profile["local_ip"], profile["interface_index"])
    if profile != expected:
        raise ValueError("Profil monitoringu jest nieprawidłowy.")
    target = Path(directory) / "profile.json"
    _save(target, profile)
    return target


def _observed(result):
    rows = {}
    for item in result.get("observed", []):
        if item.get("evidence") != "ICMP":
            continue
        ip = str(ipaddress.IPv4Address(item["ip"]))
        mac = str(item.get("mac") or "").lower()
        rows[ip] = {"ip": ip, "mac": mac, "hostname": str(item.get("hostname") or "")[:253],
                    "vendor": str(item.get("vendor") or "")[:200]}
    return rows


def compare_observations(before, after, *, complete=True):
    if not complete or before is None:
        return []
    events = []
    previous_mac = {row.get("mac"): ip for ip, row in before.items()
                    if isinstance(row, dict) and row.get("mac")}
    for ip, row in after.items():
        old = before.get(ip)
        if old is None:
            changed_ip = previous_mac.get(row["mac"]) if row["mac"] else None
            events.append({"type": "IP_CHANGE" if changed_ip else "NEW_OBSERVATION",
                           "ip": ip, "previous_ip": changed_ip,
                           "note": "Adres urządzenia się zmienił; sprawdź DHCP." if changed_ip
                           else "Nowa odpowiedź na skan; nie dowodzi obecności intruza."})
        elif old["mac"] and row["mac"] and old["mac"] != row["mac"]:
            events.append({"type": "POSSIBLE_MAC_CHANGE", "ip": ip,
                           "note": "Adres MAC przy IP się zmienił; sprawdź DHCP i losowanie MAC."})
    return events


def run_watch(directory, *, scopes_reader=local_scopes, scanner=scan_local_scope,
              now=None):
    directory = Path(directory)
    profile = _read(directory / "profile.json")
    expected = make_profile(profile["scope"], profile["local_ip"], profile["interface_index"])
    if profile != expected:
        raise ValueError("Nieprawidłowy profil monitoringu.")
    active = scopes_reader()
    if not any(row.get("scope") == profile["scope"] and
               row.get("ip") == profile["local_ip"] and
               row.get("index") == profile["interface_index"] for row in active):
        report = {"schema_version": 1, "status": "SKIPPED",
                  "timestamp": (now or datetime.now(timezone.utc)).isoformat(),
                  "reason": "Sieć lub adapter zmieniły się; bez skanu.",
                  "events": [], "observed_count": 0, "system_changed": False}
        _save(directory / "latest.json", report)
        return report
    result = scanner(profile["scope"], profile["local_ip"],
                     use_nmap=False, resolve_names=False)
    complete = result.get("status") == "COMPLETE" and not result.get("cancelled")
    current = _observed(result)
    baseline_path = directory / "last-complete.json"
    before = None
    if baseline_path.exists():
        baseline = _read(baseline_path)
        if (isinstance(baseline, dict) and baseline.get("schema_version") == 1
                and baseline.get("scope") == profile["scope"]
                and isinstance(baseline.get("devices"), dict)):
            before = baseline.get("devices")
    events = compare_observations(before, current, complete=complete)
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    report = {"schema_version": 1, "timestamp": stamp,
              "status": "COMPLETE" if complete else "PARTIAL",
              "scope": profile["scope"], "observed_count": len(current),
              "probe_errors": result.get("probe_errors", 0), "events": events,
              "system_changed": False,
              "note": "Brak odpowiedzi nie dowodzi, że urządzenie jest offline. Skan nie wykrywa wszystkich ataków."}
    _save(directory / "latest.json", report)
    if events:
        journal = directory / "events.jsonl"
        if journal.is_symlink() or (journal.exists() and journal.stat().st_size > 2 * 1024 * 1024):
            raise ValueError("Dziennik zdarzeń wymaga archiwizacji; wynik zapisano w latest.json.")
        with journal.open("a", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps({"timestamp": stamp, **event}, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
    if complete:
        _save(baseline_path, {"schema_version": 1, "scope": profile["scope"],
                              "timestamp": stamp, "devices": current})
    return report


def read_event_history(directory, *, limit=100):
    if not 1 <= limit <= 500:
        raise ValueError("Niedozwolony limit historii.")
    path = Path(directory) / "events.jsonl"
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Dziennik zdarzeń jest zbyt duży lub jest dowiązaniem.")
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if isinstance(row, dict) and row.get("type") in {
                "NEW_OBSERVATION", "POSSIBLE_MAC_CHANGE", "IP_CHANGE"}:
            rows.append(row)
    return rows[-limit:]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Odczytowy monitoring własnej podsieci")
    parser.add_argument("action", choices=("run", "show"))
    parser.add_argument("--directory", type=Path, default=None)
    args = parser.parse_args(argv)
    directory = args.directory or default_directory()
    result = run_watch(directory) if args.action == "run" else _read(directory / "latest.json")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
