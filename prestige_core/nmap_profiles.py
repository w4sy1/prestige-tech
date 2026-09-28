"""Ograniczone profile Nmap i bezpieczny odczyt wyników XML."""

import ipaddress
import os
from pathlib import Path
import re
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET


PROFILES = {
    "quick": ("-sT", "--top-ports", "100"),
    "lan-discovery": ("-sn",),
    "service-detection": ("-sT", "-sV", "--version-light", "--top-ports", "100"),
    "localhost-audit": ("-sT", "-p", "1-1024"),
    "tcp-audit": ("-sT", "--top-ports", "1000"),
    "basic-udp": ("-sU", "--top-ports", "20"),
}


def plan_profile(profile, target, *, authorized=False):
    if profile not in PROFILES:
        raise ValueError("Nieznany profil Nmap.")
    if target.lower() == "localhost":
        target = "127.0.0.1"
    try:
        network = ipaddress.ip_network(target, strict=False)
    except ValueError:
        try:
            hostname = target.encode("idna").decode("ascii")
        except UnicodeError as error:
            raise ValueError("Nieprawidłowa nazwa hosta.") from error
        labels = hostname.rstrip(".").split(".")
        if len(hostname) > 253 or not all(re.fullmatch(
                r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in labels):
            raise ValueError("Nieprawidłowa nazwa hosta.")
        if not authorized or profile == "localhost-audit":
            raise ValueError("Nazwa hosta wymaga zgody na skan i profilu innego niż localhost-audit.")
        normalized = hostname
        ipv6 = False
    else:
        if network.num_addresses > 256:
            raise ValueError("Maksymalnie 256 adresów na uruchomienie.")
        if not network.is_loopback and not authorized:
            raise ValueError("Wymagana zgoda na skan własnego lub uzgodnionego celu.")
        if profile == "localhost-audit" and not network.is_loopback:
            raise ValueError("Ten profil jest tylko dla localhost.")
        normalized = str(network) if "/" in target else str(network.network_address)
        ipv6 = network.version == 6
    return ["nmap", *(["-6"] if ipv6 else []), *PROFILES[profile], "-T3",
            "--max-retries", "1", "--host-timeout", "60s", normalized]


def parse_xml(path):
    path = Path(path)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("XML Nmap jest zbyt duży.")
    content = path.read_text(encoding="utf-8")
    if "<!DOCTYPE" in content.upper() or "<!ENTITY" in content.upper():
        raise ValueError("Deklaracje DTD nie są obsługiwane.")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise ValueError("Błędny XML Nmap.") from error
    if root.tag != "nmaprun":
        raise ValueError("To nie jest XML Nmap.")
    hosts = {}
    for host in root.findall("host"):
        addresses = [row.get("addr") for row in host.findall("address")
                     if row.get("addrtype") in {"ipv4", "ipv6"}]
        if not addresses:
            continue
        try:
            address = str(ipaddress.ip_address(addresses[0]))
        except ValueError:
            continue
        ports = {}
        for row in host.findall("./ports/port"):
            try:
                ident = f"{row.get('protocol')}/{int(row.get('portid'))}"
            except (TypeError, ValueError):
                continue
            state = row.find("state")
            service = row.find("service")
            ports[ident] = {"state": state.get("state") if state is not None else "unknown",
                            "service": dict(service.attrib) if service is not None else {}}
        status = host.find("status")
        hosts[address] = {"status": status.get("state") if status is not None else "unknown",
                          "ports": ports}
    return hosts


def compare_results(before, after):
    changes = []
    for host in sorted(before.keys() | after.keys()):
        if host not in before:
            changes.append({"host": host, "event": "NEW_HOST"})
            continue
        if host not in after:
            changes.append({"host": host, "event": "REMOVED_HOST"})
            continue
        left, right = before[host]["ports"], after[host]["ports"]
        for port in sorted(left.keys() | right.keys()):
            if port not in left:
                event = "NEW_PORT"
            elif port not in right:
                event = "PORT_NOT_IN_RESULT"
            elif left[port]["state"] != right[port]["state"]:
                event = "PORT_STATE_CHANGE"
            elif left[port]["service"] != right[port]["service"]:
                event = "SERVICE_CHANGE"
            else:
                continue
            changes.append({"host": host, "port": port, "event": event,
                            "before": left.get(port), "after": right.get(port)})
    return {"changes": changes,
            "note": "Brak portu w wyniku nie dowodzi jego zamknięcia; porównuj zgodne profile."}


def run_profile(profile, target, directory, *, authorized=False, runner=subprocess.run,
                is_admin=None, cancel_event=None):
    command = plan_profile(profile, target, authorized=authorized)
    if profile == "basic-udp":
        if is_admin is None:
            if os.name == "nt":
                import ctypes
                is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
            else:
                is_admin = os.geteuid() == 0
        if not is_admin:
            raise PermissionError("Profil UDP wymaga administratora.")
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError("Wymagany katalog raportów.")
    xml_path = directory / f"nmap-{uuid.uuid4().hex}.xml"
    with xml_path.open("x", encoding="utf-8"):
        pass
    full_command = command[:-1] + ["-oX", str(xml_path), command[-1]]
    try:
        if cancel_event is None:
            result = runner(full_command, capture_output=True, text=True, timeout=900, check=False)
        else:
            process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True)
            started = time.monotonic()
            while True:
                if cancel_event.is_set() or time.monotonic() - started > 900:
                    process.terminate()
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                    raise RuntimeError(f"Skan Nmap przerwany lub przekroczył limit czasu; plik: {xml_path}")
                try:
                    stdout, stderr = process.communicate(timeout=0.25)
                    result = subprocess.CompletedProcess(full_command, process.returncode, stdout, stderr)
                    break
                except subprocess.TimeoutExpired:
                    continue
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Nie ukończono Nmap; plik: {xml_path}") from error
    if result.returncode:
        raise RuntimeError(f"Nmap zakończył się błędem; sprawdź plik: {xml_path}")
    return {"hosts": parse_xml(xml_path), "xml": str(xml_path), "profile": profile}
