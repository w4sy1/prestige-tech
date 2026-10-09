"""Prosty opis wyniku skanu portów bez przypisywania mu diagnozy ataku."""


KNOWN = {
    "tcp/21": "FTP: sprawdź, czy usługa jest potrzebna; zwykle przesyła dane bez szyfrowania.",
    "tcp/22": "SSH: dostęp zdalny; sprawdź uprawnienia i aktualizacje.",
    "tcp/23": "Telnet: stary dostęp zdalny bez szyfrowania; warto go wyłączyć, jeśli niepotrzebny.",
    "tcp/80": "HTTP: sprawdź, czy panel urządzenia wymaga logowania i czy ma HTTPS.",
    "tcp/139": "Usługi udostępniania Windows: sprawdź, czy są potrzebne w tej sieci.",
    "tcp/445": "Udostępnianie plików Windows: ogranicz dostęp do zaufanej sieci.",
    "tcp/3389": "Pulpit zdalny: sprawdź, kto może się łączyć i czy usługa jest potrzebna.",
    "tcp/5900": "VNC: zdalny pulpit; sprawdź hasło i dostępność tylko dla zaufanych osób.",
}


def explain_hosts(hosts):
    findings = []
    for address, host in sorted(hosts.items()):
        for port, details in sorted(host.get("ports", {}).items()):
            if details.get("state") != "open":
                continue
            findings.append({"host": address, "port": port,
                             "advice": KNOWN.get(port, "Otwarta usługa: sprawdź, czy jest potrzebna i aktualna."),
                             "certainty": "OBSERVATION"})
    return {"findings": findings,
            "note": "Otwarty port nie dowodzi włamania. Wynik zależy od miejsca skanowania i zapory."}
