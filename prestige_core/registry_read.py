"""Odczytowe operacje rejestru Windows; bez tworzenia lub zmiany kluczy."""

from dataclasses import dataclass, replace
import os


@dataclass(frozen=True)
class ReadOperation:
    id: str
    name: str
    category: str
    purpose: str
    hive: str
    key: str
    values: tuple[str, ...] | None
    source: str
    risk: str = "read_only"
    view: str = "native"


SHELL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
RUN_BASE = r"Software\Microsoft\Windows\CurrentVersion"
SHELL_SOURCE = "https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/change-personal-folder-location-fails"
RUN_SOURCE = "https://learn.microsoft.com/en-us/windows/win32/setupapi/run-and-runonce-registry-keys"
ADVANCED_KEY = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
UAC_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
PROXY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
RDP_KEY = r"SYSTEM\CurrentControlSet\Control\Terminal Server"
PATHS_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion"
VERSION_KEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
EXPLORER_SOURCE = "https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-gppref/a6ca3a17-1971-4b22-bf3b-e1a5d5c50fca"
UAC_SOURCE = "https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/settings-and-configuration"
PROXY_SOURCE = "https://learn.microsoft.com/en-us/windows/win32/wininet/enabling-internet-functionality"
RDP_SOURCE = "https://learn.microsoft.com/en-us/troubleshoot/windows-server/remote/remote-desktop-cannot-connect-remote-computer"
PATHS_SOURCE = "https://learn.microsoft.com/en-us/powershell/scripting/samples/working-with-registry-entries"
BUILD_SOURCE = "https://learn.microsoft.com/en-us/intune/app-management/deployment/deploy-win32-update-package"

OPERATIONS = (
    ReadOperation(
        "REG-READ-001", "Lokalizacje folderów użytkownika", "Explorer",
        "Odczytaj skonfigurowane ścieżki siedmiu folderów osobistych.", "HKCU", SHELL_KEY,
        ("Desktop", "Personal", "My Music", "My Pictures", "My Video", "Favorites",
         "{374DE290-123F-4565-9164-39C4925E467B}"), SHELL_SOURCE,
    ),
    ReadOperation(
        "REG-READ-002", "Autostart bieżącego użytkownika (Run)", "Logowanie",
        "Odczytaj wpisy uruchamiane podczas logowania bieżącego użytkownika.",
        "HKCU", RUN_BASE + r"\Run", None, RUN_SOURCE,
    ),
    ReadOperation(
        "REG-READ-003", "Jednorazowy autostart użytkownika (RunOnce)", "Logowanie",
        "Odczytaj wpisy RunOnce; sam odczyt nie wykonuje poleceń.",
        "HKCU", RUN_BASE + r"\RunOnce", None, RUN_SOURCE,
    ),
    ReadOperation(
        "REG-READ-004", "Autostart komputera (Run)", "Logowanie",
        "Odczytaj wpisy Run wspólne dla komputera; użyj natywnego widoku rejestru.",
        "HKLM", RUN_BASE + r"\Run", None, RUN_SOURCE,
    ),
    ReadOperation(
        "REG-READ-005", "Jednorazowy autostart komputera (RunOnce)", "Logowanie",
        "Odczytaj wpisy RunOnce wspólne dla komputera; sam odczyt ich nie uruchamia.",
        "HKLM", RUN_BASE + r"\RunOnce", None, RUN_SOURCE,
    ),
)

# Każdy wpis jest oddzielnym, odczytowym działaniem na jednej udokumentowanej
# wartości. Brak wartości jest jawnie oznaczany jako Niedostępne.
_SINGLE_VALUE_READS = (
    (6, "Rozszerzenia znanych plików", "Explorer", "HKCU", ADVANCED_KEY, "HideFileExt", EXPLORER_SOURCE),
    (7, "Widoczność plików ukrytych", "Explorer", "HKCU", ADVANCED_KEY, "Hidden", EXPLORER_SOURCE),
    (8, "Widoczność chronionych plików", "Explorer", "HKCU", ADVANCED_KEY, "ShowSuperHidden", EXPLORER_SOURCE),
    (9, "Nakładki ikon miniatur", "Explorer", "HKCU", ADVANCED_KEY, "ShowTypeOverlay", EXPLORER_SOURCE),
    (10, "Oddzielny proces Eksploratora", "Explorer", "HKCU", ADVANCED_KEY, "SeparateProcess", EXPLORER_SOURCE),
    (11, "Podpowiedzi plików", "Explorer", "HKCU", ADVANCED_KEY, "ShowInfoTip", EXPLORER_SOURCE),
    (12, "Kolory plików NTFS", "Explorer", "HKCU", ADVANCED_KEY, "ShowCompColor", EXPLORER_SOURCE),
    (13, "Główne ustawienie UAC", "UAC", "HKLM", UAC_KEY, "EnableLUA", UAC_SOURCE),
    (14, "Monit administratora UAC", "UAC", "HKLM", UAC_KEY, "ConsentPromptBehaviorAdmin", UAC_SOURCE),
    (15, "Monit użytkownika UAC", "UAC", "HKLM", UAC_KEY, "ConsentPromptBehaviorUser", UAC_SOURCE),
    (16, "Wykrywanie instalatorów UAC", "UAC", "HKLM", UAC_KEY, "EnableInstallerDetection", UAC_SOURCE),
    (17, "Weryfikacja podpisów UAC", "UAC", "HKLM", UAC_KEY, "ValidateAdminCodeSignatures", UAC_SOURCE),
    (18, "Bezpieczne lokalizacje UIAccess", "UAC", "HKLM", UAC_KEY, "EnableSecureUIAPaths", UAC_SOURCE),
    (19, "Bezpieczny pulpit monitów UAC", "UAC", "HKLM", UAC_KEY, "PromptOnSecureDesktop", UAC_SOURCE),
    (20, "Wirtualizacja plików i rejestru UAC", "UAC", "HKLM", UAC_KEY, "EnableVirtualization", UAC_SOURCE),
    (21, "Monity UIAccess poza bezpiecznym pulpitem", "UAC", "HKLM", UAC_KEY, "EnableUIADesktopToggle", UAC_SOURCE),
    (22, "Włączenie proxy użytkownika", "Sieć", "HKCU", PROXY_KEY, "ProxyEnable", PROXY_SOURCE),
    (23, "Zezwolenie na połączenia RDP", "Zdalny dostęp", "HKLM", RDP_KEY, "fDenyTSConnections", RDP_SOURCE),
    (24, "Ścieżka katalogu sterowników", "System", "HKLM", PATHS_KEY, "DevicePath", PATHS_SOURCE),
    (25, "Ścieżka Program Files", "System", "HKLM", PATHS_KEY, "ProgramFilesDir", PATHS_SOURCE),
    (26, "Tryb zatwierdzania wbudowanego administratora", "UAC", "HKLM", UAC_KEY, "FilterAdministratorToken", UAC_SOURCE),
    (27, "Priorytet logowania sieciowego", "UAC", "HKLM", UAC_KEY, "InteractiveLogonFirst", UAC_SOURCE),
    (28, "Numer kompilacji Windows", "System", "HKLM", VERSION_KEY, "CurrentBuildNumber", BUILD_SOURCE),
    (29, "Rewizja kompilacji Windows", "System", "HKLM", VERSION_KEY, "UBR", BUILD_SOURCE),
)

OPERATIONS += tuple(ReadOperation(f"REG-READ-{number:03d}", name, category,
                                  f"Odczytaj wartość {value} bez zmiany rejestru.",
                                  hive, key, (value,), source)
                    for number, name, category, hive, key, value, source in _SINGLE_VALUE_READS)


def read_operation(operation, *, registry=None, platform=None, catalog=OPERATIONS):
    if (platform or os.name) != "nt":
        raise RuntimeError("Odczyt rejestru wymaga Windows.")
    if registry is None:
        import winreg as registry
    if operation not in catalog:
        raise ValueError("Operacja nie należy do zatwierdzonego katalogu.")
    if operation.hive == "BOTH":
        results = []
        for scope in ("HKCU", "HKLM"):
            scoped = replace(operation, hive=scope)
            result = read_operation(scoped, registry=registry, platform=platform,
                                    catalog=(scoped,))
            results.append((scope, result))
        rows = [{**row, "name": f"{scope}: {row['name']}"}
                for scope, result in results for row in result["rows"]]
        status = "OK" if any(result["status"] == "OK" for _, result in results) else "Niedostępne"
        return {"operation": operation.id, "status": status,
                "reason": None if status == "OK" else "Zasada nieustawiona w HKCU ani HKLM.",
                "rows": rows}
    hive = {"HKCU": registry.HKEY_CURRENT_USER,
            "HKLM": registry.HKEY_LOCAL_MACHINE}[operation.hive]
    try:
        with registry.OpenKey(hive, operation.key, 0, registry.KEY_READ) as handle:
            rows = []
            if operation.values is not None:
                for name in operation.values:
                    try:
                        value, data_type = registry.QueryValueEx(handle, name)
                        rows.append({"name": name, "value": str(value), "type": data_type, "status": "OK"})
                    except FileNotFoundError:
                        rows.append({"name": name, "value": None, "type": None, "status": "Niedostępne"})
            else:
                index = 0
                while True:
                    try:
                        name, value, data_type = registry.EnumValue(handle, index)
                    except OSError as error:
                        if getattr(error, "winerror", None) == 259:
                            break
                        raise
                    rows.append({"name": name, "value": str(value), "type": data_type, "status": "OK"})
                    index += 1
    except FileNotFoundError:
        return {"operation": operation.id, "status": "Niedostępne", "reason": "Klucz nie istnieje.", "rows": []}
    except PermissionError:
        return {"operation": operation.id, "status": "Niedostępne", "reason": "Odmowa dostępu.", "rows": []}
    return {"operation": operation.id, "status": "OK", "reason": None, "rows": rows}
