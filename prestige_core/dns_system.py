"""Odczytowe funkcje DNS Center; bez zmiany konfiguracji resolverów."""

import ipaddress
import json
import os
import subprocess
import sys

from .security_check import _powershell


def read_doh_state(*, runner=None, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt DoH wymaga Windows.")
    script = ("if(-not (Get-Command Get-DnsClientDohServerAddress -ErrorAction SilentlyContinue)){"
              "@{available=$false;servers=@()}|ConvertTo-Json -Compress -Depth 4;return};"
              "$rows=@(Get-DnsClientDohServerAddress -ErrorAction Stop | "
              "Select-Object ServerAddress,DohTemplate,AllowFallbackToUdp,AutoUpgrade);"
              "@{available=$true;servers=$rows}|ConvertTo-Json -Compress -Depth 4")
    options = {"runner": runner} if runner is not None else {}
    data = _powershell(script, 30, **options)
    if (not isinstance(data, dict) or type(data.get("available")) is not bool
            or not isinstance(data.get("servers"), list)):
        raise RuntimeError("Nieprawidłowy wynik odczytu DoH.")
    return {"status": "AVAILABLE" if data["available"] else "UNAVAILABLE",
            "servers": data["servers"],
            "note": "Rejestracja serwera DoH nie dowodzi, że przeglądarka lub system używa go teraz."}


def system_dns_test(host="example.com", *, runner=subprocess.run):
    if not isinstance(host, str) or not host or len(host) > 253 or any(
            not part or len(part) > 63 or not all(c.isalnum() or c == "-" for c in part)
            for part in host.split(".")):
        raise ValueError("Nieprawidłowa nazwa DNS.")
    code = ("import json,socket,sys;"
            "rows=socket.getaddrinfo(sys.argv[1],443,type=socket.SOCK_STREAM);"
            "print(json.dumps(sorted({r[4][0] for r in rows})[:10]))")
    try:
        result = runner([sys.executable, "-c", code, host], capture_output=True,
                        text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"status": "UNKNOWN", "host": host, "addresses": [],
                "error": type(error).__name__}
    if result.returncode:
        return {"status": "UNKNOWN", "host": host, "addresses": [],
                "error": "ResolverError"}
    try:
        values = json.loads(result.stdout)
        if not isinstance(values, list) or len(values) > 10:
            raise ValueError
        addresses = [str(ipaddress.ip_address(value)) for value in values]
    except (ValueError, TypeError) as error:
        raise RuntimeError("Resolver zwrócił nieprawidłowy wynik.") from error
    return {"status": "OK" if addresses else "UNKNOWN", "host": host,
            "addresses": addresses,
            "note": "Test używa bieżącej konfiguracji systemu; nie wskazuje użytego serwera DNS."}
