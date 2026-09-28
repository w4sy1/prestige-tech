"""Odczytowa migracja ADB Diagnostic i Android Inspector."""

import re
import subprocess
from collections import Counter


PROPERTIES = {
    "model": "ro.product.model", "manufacturer": "ro.product.manufacturer",
    "android": "ro.build.version.release", "security_patch": "ro.build.version.security_patch",
    "cpu_abi": "ro.product.cpu.abi", "soc_model": "ro.soc.model",
    "hardware": "ro.hardware",
}
COMMANDS = {
    "kernel": ["uname", "-r"], "ram": ["cat", "/proc/meminfo"],
    "storage": ["df", "-k", "/data"], "battery": ["dumpsys", "battery"],
    "uptime": ["cat", "/proc/uptime"], "usb": ["getprop", "sys.usb.state"],
    "network": ["ip", "address"],
    "packages": ["pm", "list", "packages"],
    "user_apps": ["pm", "list", "packages", "-3"],
    "services": ["service", "list"],
    "permissions": ["pm", "list", "permissions", "-g"],
}
_SERIAL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_PACKAGE = re.compile(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+\Z")
SPECIAL = {
    "android.permission.SYSTEM_ALERT_WINDOW": "overlay",
    "android.permission.REQUEST_INSTALL_PACKAGES": "unknown sources",
    "android.permission.BIND_ACCESSIBILITY_SERVICE": "Accessibility",
    "android.permission.BIND_VPN_SERVICE": "VPN",
    "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": "notification access",
    "android.permission.BIND_DEVICE_ADMIN": "Device Admin",
}


class AdbBackend:
    def __init__(self, *, runner=subprocess.run):
        self.runner = runner

    def run(self, args, *, timeout=30):
        try:
            result = self.runner(["adb", *args], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=timeout, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            raise RuntimeError("ADB jest niedostępne lub polecenie przekroczyło limit czasu.") from error
        if result.returncode:
            raise RuntimeError("Polecenie ADB nie powiodło się.")
        output = result.stdout or ""
        if len(output) > 100000:
            raise RuntimeError("Odpowiedź ADB przekroczyła limit 100 000 znaków.")
        return output


def parse_devices(text):
    devices = []
    for line in text.splitlines():
        if line.startswith("List of devices") or not line.strip() or line.startswith("* daemon"):
            continue
        fields = line.split()
        if len(fields) < 2 or not _SERIAL.fullmatch(fields[0]):
            continue
        devices.append({"serial": fields[0], "state": fields[1],
                        "authorized": fields[1] == "device"})
    return devices


def list_devices(backend):
    return parse_devices(backend.run(["devices", "-l"], timeout=15))


def require_device(serial, devices):
    if serial is None:
        ready = [row["serial"] for row in devices if row["authorized"]]
        if len(ready) != 1:
            raise ValueError("Wybierz jedno autoryzowane urządzenie ADB.")
        return ready[0]
    if not _SERIAL.fullmatch(serial) or not any(
            row["serial"] == serial and row["authorized"] for row in devices):
        raise ValueError("Urządzenie ADB jest niedostępne lub nieautoryzowane.")
    return serial


def parse_battery(text):
    result = {}
    for line in text.splitlines():
        key, separator, value = line.strip().partition(":")
        if separator and key in {"level", "scale", "status", "health", "voltage",
                                 "temperature", "AC powered", "USB powered"}:
            result[key] = value.strip()
    try:
        result["temperature_c"] = int(result["temperature"]) / 10
    except (KeyError, ValueError):
        result["temperature_c"] = None
    return result


def logcat_summary(text):
    counts, first, last, unparsed = Counter(), None, None, 0
    pattern = re.compile(r"^(\d\d-\d\d\s+\d\d:\d\d:\d\d\.\d+)\s+\d+\s+\d+\s+([EF])\s+([^:]{1,120}):")
    for line in text.splitlines():
        if not line or line.startswith("---------"):
            continue
        match = pattern.match(line)
        if not match:
            unparsed += 1
            continue
        stamp, priority, tag = match.groups()
        counts[(priority, tag.strip())] += 1
        first = first or stamp
        last = stamp
    return {"groups": [{"priority": key[0], "tag": key[1], "count": value}
                       for key, value in counts.most_common(50)],
            "total_errors": sum(counts.values()), "first_timestamp": first,
            "last_timestamp": last, "unparsed_lines": unparsed, "messages_stored": False}


def permissions_summary(text):
    grants = {name: state == "true" for name, state in
              re.findall(r"(android\.permission\.[A-Z_0-9]+):\s*granted=(true|false)", text)}
    return {"permissions": grants, "source": "dumpsys package", "complete": bool(grants)}


def read_diagnostic(serial, backend, *, include_logcat=False, package_permissions=()):
    serial = require_device(serial, list_devices(backend))
    for package in package_permissions:
        if not _PACKAGE.fullmatch(package):
            raise ValueError("Nieprawidłowa nazwa pakietu Android.")
    base = ["-s", serial, "shell"]
    results = {}
    for name, command in {**{name: ["getprop", property_name]
                            for name, property_name in PROPERTIES.items()}, **COMMANDS}.items():
        try:
            value = backend.run(base + command)
            results[name] = {"status": "OK" if value.strip() else "EMPTY",
                             "data": parse_battery(value) if name == "battery" else value.strip()}
        except RuntimeError:
            results[name] = {"status": "UNAVAILABLE"}
    if include_logcat:
        try:
            text = backend.run(["-s", serial, "logcat", "-d", "-t", "200", "-v", "threadtime", "*:E"],
                               timeout=20)
            results["logcat"] = {"status": "OK", "data": logcat_summary(text)}
        except RuntimeError:
            results["logcat"] = {"status": "UNAVAILABLE"}
    for package in package_permissions:
        try:
            text = backend.run(base + ["dumpsys", "package", package])
            results["permissions:" + package] = {"status": "OK", "data": permissions_summary(text)}
        except RuntimeError:
            results["permissions:" + package] = {"status": "UNAVAILABLE"}
    return {"serial": serial, "results": results,
            "status": "UNKNOWN" if any(row["status"] == "UNAVAILABLE" for row in results.values())
            else "COMPLETE", "note": "Odczyt ADB nie zmienia konfiguracji telefonu."}


def parse_package(package, text):
    if not _PACKAGE.fullmatch(package):
        raise ValueError("Nieprawidłowa nazwa pakietu Android.")
    def field(name):
        match = re.search(r"\b" + name + r"=([^\r\n]+)", text)
        return match.group(1).strip() if match else None
    requested, in_section = [], False
    for line in text.splitlines():
        if line.strip() == "requested permissions:":
            in_section = True
            continue
        if in_section:
            match = re.fullmatch(r"\s+(android\.permission\.[A-Z_0-9]+)\s*", line)
            if match:
                requested.append(match.group(1))
            elif line.strip():
                in_section = False
    granted = {name: value == "true" for name, value in
               re.findall(r"(android\.permission\.[A-Z_0-9]+):\s*granted=(true|false)", text)}
    special = [label for permission, label in SPECIAL.items()
               if permission in requested or permission in text]
    return {"package": package, "version": field("versionName"),
            "first_install": field("firstInstallTime"), "last_update": field("lastUpdateTime"),
            "installer": field("installerPackageName"), "requested_permissions": requested,
            "granted_permissions": granted, "special_indicators": special,
            "interest": "WARTO SPRAWDZIĆ" if special else "NORMAL",
            "note": "Deklaracja uprawnienia nie dowodzi aktywnego dostępu ani malware."}


def parse_appops(text):
    result = {}
    for operation, label in {"SYSTEM_ALERT_WINDOW": "overlay",
                             "REQUEST_INSTALL_PACKAGES": "unknown sources"}.items():
        match = re.search(r"(?mi)^\s*" + operation + r":\s*(allow|ignore|deny|default|foreground)\b", text)
        mode = match.group(1).lower() if match else None
        result[label] = {"mode": mode, "active": True if mode == "allow" else
                         False if mode in {"ignore", "deny"} else None,
                         "status": "OBSERVED" if mode else "UNKNOWN"}
    return result


def parse_admins(text):
    packages = set()
    for line in text.splitlines():
        if re.search(r"(?i)(active\s+admin|enabled\s+device\s+admins|admin=|device\s*owner|profile\s*owner)", line):
            packages.update(re.findall(r"\b([A-Za-z][\w]*(?:\.[\w]+)+)/[\w.$]+", line))
    return packages


def inspect_apps(serial, backend, *, include_system=False, limit=200):
    if type(limit) is not int or not 1 <= limit <= 2000:
        raise ValueError("Limit aplikacji musi być w zakresie 1–2000.")
    serial = require_device(serial, list_devices(backend))
    base = ["-s", serial, "shell"]
    command = base + ["pm", "list", "packages"] + ([] if include_system else ["-3"])
    names = [line.removeprefix("package:").strip() for line in backend.run(command).splitlines()
             if line.startswith("package:")]
    roles = {}
    for key in ("enabled_accessibility_services", "enabled_notification_listeners", "always_on_vpn_app"):
        try:
            roles[key] = backend.run(base + ["settings", "get", "secure", key]).strip()
        except RuntimeError:
            roles[key] = "UNAVAILABLE"
    try:
        policy = backend.run(base + ["dumpsys", "device_policy"])
        active_admins = parse_admins(policy)
        admin_coverage = "OBSERVED" if "Device Policy" in policy or "Enabled Device Admins" in policy else "UNKNOWN"
    except RuntimeError:
        active_admins, admin_coverage = set(), "UNKNOWN"
    apps = []
    for package in names[:limit]:
        if not _PACKAGE.fullmatch(package):
            apps.append({"package": package[:200], "status": "UNKNOWN"})
            continue
        try:
            app = parse_package(package, backend.run(base + ["dumpsys", "package", package]))
            app["active_special_access"] = [key for key, value in roles.items()
                                            if value != "UNAVAILABLE" and
                                            package in re.split(r"[:/]", value)]
            if package in active_admins:
                app["active_special_access"].append("Device Admin")
            app["device_admin_status"] = "ACTIVE" if package in active_admins else admin_coverage
            try:
                app["appops"] = parse_appops(backend.run(base + ["cmd", "appops", "get", package], timeout=15))
            except RuntimeError:
                app["appops"] = parse_appops("")
            app["active_special_access"].extend(key for key, value in app["appops"].items()
                                                if value["active"] is True)
            app["role_coverage"] = {key: "UNKNOWN" if value == "UNAVAILABLE" else "OBSERVED"
                                    for key, value in roles.items()}
            if len(app["active_special_access"]) >= 2:
                app["interest"] = "NIETYPOWE"
            elif app["active_special_access"]:
                app["interest"] = "WARTO SPRAWDZIĆ"
            apps.append(app)
        except RuntimeError:
            apps.append({"package": package, "status": "UNAVAILABLE"})
    return {"serial": serial, "apps": apps, "device_admin_coverage": admin_coverage,
            "truncated": len(names) > limit,
            "status": "UNKNOWN" if len(names) > limit or any(row.get("status") for row in apps)
            else "COMPLETE",
            "note": "Appops default/foreground i brak wpisu nie dowodzą zgody. Device Admin zależy od OEM."}
