"""Lokalny kontekst łącza Windows bez sond zewnętrznych."""

import base64
import ipaddress
import json
import os
import re
import subprocess


def parse_wifi(text):
    result = {}
    patterns = {"signal_percent": r"(?:Signal|Sygnał)\s*:\s*(\d+)\s*%",
                "receive_mbps": r"(?:Receive rate|Szybkość odbierania).*?:\s*([\d.,]+)",
                "transmit_mbps": r"(?:Transmit rate|Szybkość transmisji).*?:\s*([\d.,]+)"}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.I)
        if match:
            result[key] = float(match.group(1).replace(",", "."))
    if "signal_percent" in result:
        result["estimated_rssi_dbm"] = result["signal_percent"] / 2 - 100
        result["rssi_kind"] = "estimate_from_signal_quality_not_direct_measurement"
    return result


def read_context(*, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Kontekst łącza jest obecnie dostępny na Windows.")
    script = r'''
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$routes=@(Get-NetRoute -DestinationPrefix '0.0.0.0/0' -ErrorAction Stop |
 Where-Object NextHop -ne '0.0.0.0' | Sort-Object @{Expression={$_.RouteMetric+$_.InterfaceMetric}})
$gateway=$null;if($routes.Count){$gateway=$routes[0].NextHop}
[pscustomobject]@{gateway=$gateway;interfaces=@(Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=True' -ErrorAction Stop |
 Select-Object InterfaceIndex,Description,DHCPEnabled,DHCPServer,DNSServerSearchOrder,DefaultIPGateway,IPAddress,IPSubnet,MACAddress);
 links=@(Get-NetAdapter -ErrorAction Stop | Select-Object InterfaceIndex,Name,Status,LinkSpeed)} |
 ConvertTo-Json -Depth 6 -Compress
'''
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    try:
        result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                        capture_output=True, text=True, encoding="utf-8", timeout=25, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError("Nie odczytano kontekstu sieci.") from error
    if result.returncode:
        raise RuntimeError("Nie odczytano kontekstu sieci.")
    try:
        payload = json.loads((result.stdout or "").lstrip("\ufeff"))
    except json.JSONDecodeError as error:
        raise RuntimeError("Kontekst sieci ma nieprawidłowy format.") from error
    if not isinstance(payload, dict):
        raise RuntimeError("Kontekst sieci ma nieprawidłowy format.")
    interfaces = payload.get("interfaces") or []
    links = payload.get("links") or []
    if isinstance(interfaces, dict):
        interfaces = [interfaces]
    if isinstance(links, dict):
        links = [links]
    if not isinstance(interfaces, list) or not isinstance(links, list):
        raise RuntimeError("Nieprawidłowa lista interfejsów.")
    dns = []
    for row in interfaces:
        if not isinstance(row, dict):
            continue
        values = row.get("DNSServerSearchOrder") or []
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list):
            continue
        for value in values:
            try:
                address = str(ipaddress.ip_address(value))
            except (ValueError, TypeError):
                continue
            if address not in dns:
                dns.append(address)
    gateway = payload.get("gateway")
    try:
        gateway = str(ipaddress.IPv4Address(gateway)) if gateway else None
    except (ValueError, TypeError):
        gateway = None
    errors = []
    try:
        wifi_result = runner(["netsh", "wlan", "show", "interfaces"], capture_output=True,
                             text=True, encoding="utf-8", timeout=15, check=False)
        wifi = parse_wifi(wifi_result.stdout or "") if wifi_result.returncode == 0 else {}
        if wifi_result.returncode:
            errors.append("Kontekst Wi-Fi niedostępny.")
    except (OSError, subprocess.TimeoutExpired):
        wifi = {}
        errors.append("Kontekst Wi-Fi niedostępny.")
    return {"gateway": gateway, "dns_servers": dns, "interfaces": interfaces,
            "links": links, "wifi": wifi, "errors": errors,
            "status": "UNKNOWN" if errors else "COMPLETE"}


def correlate_diagnostic(diagnostic, context):
    """Dołącz pomiar jakości Wi-Fi do wyniku, bez przypisywania mu przyczynowości."""
    wifi = context.get("wifi") if isinstance(context, dict) else None
    signal = wifi.get("signal_percent") if isinstance(wifi, dict) else None
    if diagnostic.get("status") != "COMPLETE" or type(signal) not in (int, float):
        return {"status": "UNKNOWN", "reason": "Brak kompletnego pomiaru Wi-Fi i Internetu."}
    gateway = diagnostic.get("gateway")
    internet = diagnostic.get("internet", {})
    gateway_loss = gateway.get("packet_loss_percent") if isinstance(gateway, dict) else None
    internet_loss = internet.get("packet_loss_percent") if isinstance(internet, dict) else None
    if type(gateway_loss) not in (int, float) or type(internet_loss) not in (int, float):
        return {"status": "UNKNOWN", "reason": "Brak porównywalnych próbek bramy i Internetu."}
    if signal < 40 and gateway_loss > 20:
        category = "słaby sygnał i straty do bramy"
        note = "Wi-Fi może współwystępować z problemem lokalnym; ICMP i jakość sygnału nie dowodzą przyczyny."
    elif gateway_loss <= 20 and internet_loss > 20:
        category = "straty głównie poza bramą"
        note = "Lokalny pomiar Wi-Fi nie wyjaśnia strat zdalnych; host może ograniczać ICMP."
    else:
        category = "brak jednoznacznej korelacji"
        note = "Jakość sygnału nie jest miarą przepustowości ani stabilności połączenia."
    return {"status": "CORRELATED", "signal_percent": signal,
            "estimated_rssi_dbm": wifi.get("estimated_rssi_dbm"),
            "gateway_loss_percent": gateway_loss, "internet_loss_percent": internet_loss,
            "category": category, "note": note}
