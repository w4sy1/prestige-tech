"""Pomiary połączenia znane z Internet Diagnostic, bez zmian konfiguracji sieci."""

import ipaddress
import http.client
import os
import re
import statistics
import subprocess
import sys
import time


_LATENCY = re.compile(r"(?:time|czas)\s*[=<]\s*([\d.,]+)\s*ms", re.I)
_HOST = re.compile(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}\Z")


def ping_sample(address, *, runner=subprocess.run, platform=None):
    address = str(ipaddress.ip_address(address))
    command = (["ping", "-n", "1", "-w", "1000", address] if (platform or os.name) == "nt"
               else ["ping", "-c", "1", "-W", "1", address])
    try:
        result = runner(command, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Narzędzie ping jest niedostępne.") from error
    if result.returncode:
        return None
    match = _LATENCY.search(result.stdout or "")
    if not match:
        raise RuntimeError("Nieobsługiwany format odpowiedzi ping.")
    return float(match.group(1).replace(",", "."))


def summarize(samples):
    if not samples:
        raise ValueError("Brak próbek.")
    valid = [value for value in samples if value is not None]
    adjacent = [abs(right - left) for left, right in zip(samples, samples[1:])
                if left is not None and right is not None]
    return {"samples": len(samples), "received": len(valid),
            "packet_loss_percent": 100 * (len(samples) - len(valid)) / len(samples),
            "mean_ms": statistics.mean(valid) if valid else None,
            "jitter_ms": statistics.mean(adjacent) if adjacent else None}


def classify(gateway, internet, dns_ok):
    if gateway and gateway["packet_loss_percent"] > 20:
        return {"category": "możliwy problem lokalny lub routera",
                "reason": "Brama nie odpowiedziała na część prób; może też ograniczać ICMP."}
    if internet["received"] and not dns_ok:
        return {"category": "możliwy problem DNS",
                "reason": "Host IP odpowiedział, lecz test resolvera się nie powiódł."}
    if gateway and gateway["packet_loss_percent"] == 0 and internet["packet_loss_percent"] > 20:
        return {"category": "możliwy problem dalszej trasy",
                "reason": "Brama odpowiedziała; zdalny host może ograniczać ICMP."}
    return {"category": "brak rozstrzygnięcia",
            "reason": "Te pomiary nie potwierdzają ani nie wykluczają awarii."}


def _dns_lookup(name, *, runner):
    if not _HOST.fullmatch(name):
        raise ValueError("Nieprawidłowa nazwa DNS.")
    started = time.perf_counter()
    command = [sys.executable, "-c", "import socket,sys; socket.getaddrinfo(sys.argv[1],None)", name]
    try:
        result = runner(command, capture_output=True, text=True, timeout=10, check=False)
        ok = result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        ok = False
    return {"ok": ok, "lookup_process_ms": (time.perf_counter() - started) * 1000,
            "note": "Czas obejmuje start procesu i cache systemowy, nie tylko serwer DNS."}


def mtu_probe(address, *, runner=subprocess.run, platform=None):
    address = str(ipaddress.IPv4Address(address))
    low, high, best = 576 - 28, 1500 - 28, None
    while low <= high:
        payload = (low + high) // 2
        command = (["ping", "-n", "1", "-w", "1000", "-f", "-l", str(payload), address]
                   if (platform or os.name) == "nt" else
                   ["ping", "-c", "1", "-W", "1", "-M", "do", "-s", str(payload), address])
        try:
            result = runner(command, capture_output=True, timeout=4, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {"estimated_ipv4_mtu": None, "status": "UNKNOWN"}
        if result.returncode == 0:
            best = payload + 28
            low = payload + 1
        else:
            high = payload - 1
    return {"estimated_ipv4_mtu": best, "status": "ESTIMATE" if best else "UNKNOWN",
            "note": "Brak odpowiedzi ICMP nie dowodzi fragmentacji; zakres 576–1500."}


def http_probe(host, *, secure=False, connection_factory=None):
    """HEAD / bez przekierowań i bez pobierania treści; status HTTP to nie diagnoza Internetu."""
    if not _HOST.fullmatch(host) or ":" in host or host.startswith("-"):
        raise ValueError("Nieprawidłowa nazwa hosta HTTP.")
    factory = connection_factory or (http.client.HTTPSConnection if secure
                                     else http.client.HTTPConnection)
    started = time.perf_counter()
    connection = None
    try:
        connection = factory(host, timeout=5)
        connection.request("HEAD", "/", headers={"User-Agent": "PrestigeTech-Diagnostic/1"})
        response = connection.getresponse()
        return {"status": "RESPONSE", "http_status": response.status,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)}
    except (OSError, http.client.HTTPException) as error:
        return {"status": "UNKNOWN", "error_type": type(error).__name__}
    finally:
        if connection is not None:
            connection.close()


def diagnose(target, *, gateway=None, dns_name="example.com", count=5,
             traceroute=False, test_mtu=False, test_http=False, cancel_event=None,
             runner=subprocess.run, platform=None):
    target = str(ipaddress.ip_address(target))
    gateway = str(ipaddress.ip_address(gateway)) if gateway else None
    if not 2 <= count <= 100:
        raise ValueError("Liczba próbek musi być w zakresie 2–100.")
    if not _HOST.fullmatch(dns_name):
        raise ValueError("Nieprawidłowa nazwa DNS.")

    def samples(address):
        values = []
        for _ in range(count):
            if cancel_event is not None and cancel_event.is_set():
                return None
            values.append(ping_sample(address, runner=runner, platform=platform))
        return summarize(values)

    internet = samples(target)
    if internet is None:
        return {"status": "INCOMPLETE", "reason": "Przerwano pomiar."}
    local = samples(gateway) if gateway else None
    if gateway and local is None:
        return {"status": "INCOMPLETE", "reason": "Przerwano pomiar."}
    dns = _dns_lookup(dns_name, runner=runner)
    result = {"status": "COMPLETE", "target": target, "gateway_address": gateway,
              "internet": internet, "gateway": local, "dns": dns,
              "classification": classify(local, internet, dns["ok"]),
              "note": "Brak odpowiedzi ICMP nie dowodzi niedostępności hosta."}
    if traceroute:
        command = (["tracert", "-d", "-h", "12", "-w", "500", target]
                   if (platform or os.name) == "nt" else
                   ["traceroute", "-n", "-m", "12", "-w", "1", target])
        try:
            trace = runner(command, capture_output=True, text=True, timeout=60, check=False)
            result["traceroute"] = {"status": "COMPLETE" if trace.returncode == 0 else "UNKNOWN",
                                    "output": (trace.stdout or "")[:20000]}
        except (OSError, subprocess.TimeoutExpired):
            result["traceroute"] = {"status": "UNKNOWN", "output": ""}
    if test_mtu:
        result["mtu"] = mtu_probe(target, runner=runner, platform=platform)
    if test_http:
        result["web"] = {}
        for scheme, secure in (("http", False), ("https", True)):
            if cancel_event is not None and cancel_event.is_set():
                result["web"][scheme] = {"status": "INCOMPLETE"}
            else:
                result["web"][scheme] = http_probe(dns_name, secure=secure)
    return result
