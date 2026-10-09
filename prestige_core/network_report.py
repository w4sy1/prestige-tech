"""Odczytowy raport HTML z jawnego skanu LAN i list Sentinel."""

import html
from pathlib import Path


def export_network_report(discovery, registry, destination):
    if not isinstance(discovery, dict) or not isinstance(discovery.get("observed"), list):
        raise ValueError("Najpierw wykonaj jawny skan LAN.")
    rows = []
    for item in discovery["observed"][:256]:
        if not isinstance(item, dict):
            continue
        values = [item.get(key, "") for key in ("ip", "mac", "hostname", "evidence")]
        rows.append("<tr>" + "".join(f"<td>{html.escape(str(value or ''))}</td>" for value in values) + "</tr>")
    status = str(discovery.get("status", "UNKNOWN"))
    scope = str(discovery.get("scope", "nieznany"))
    trusted = 0
    registry_quality = "nie odczytano"
    if isinstance(registry, dict):
        registry_quality = str(registry.get("status", "UNKNOWN"))
        trusted = sum(bool(item.get("trusted")) for item in registry.get("devices", [])
                      if isinstance(item, dict))
    document = ("<!doctype html><html lang='pl'><meta charset='utf-8'>"
                "<title>Prestige Tech — raport LAN</title>"
                "<style>body{font:16px system-ui;max-width:1000px;margin:40px auto}"
                "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccc;"
                "padding:8px;text-align:left;overflow-wrap:anywhere}</style>"
                "<h1>PRESTIGE TECH — raport LAN</h1>"
                f"<p>Zakres: {html.escape(scope)}; stan skanu: {html.escape(status)}; "
                f"stan list Sentinel: {html.escape(registry_quality)}; "
                f"wpisów zaufanych: {trusted}.</p>"
                "<p>ICMP/Nmap oznacza odpowiedź podczas skanu. Wpis cache nie dowodzi obecności "
                "online. Brak obserwacji nie dowodzi stanu offline ani braku urządzenia.</p>"
                "<table><tr><th>IP</th><th>MAC</th><th>Nazwa</th><th>Źródło danych</th></tr>"
                + "".join(rows) + "</table></html>")
    path = Path(destination)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(document)
    return str(path)
