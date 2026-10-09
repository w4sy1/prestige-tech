"""Odczytowy stan lokalnego środowiska Termux."""

import os
from pathlib import Path
import shutil


def health_check(*, environ=None, which=shutil.which):
    env = os.environ if environ is None else environ
    prefix = env.get("PREFIX", "")
    home = env.get("HOME", "")
    commands = {name: bool(which(name)) for name in ("pkg", "termux-info", "termux-api", "tar", "git")}
    termux = bool(prefix and "com.termux" in prefix)
    return {"status": "READY" if termux and commands["pkg"] else "UNAVAILABLE",
            "termux_detected": termux, "prefix_exists": bool(prefix and Path(prefix).is_dir()),
            "home_exists": bool(home and Path(home).is_dir()), "commands": commands,
            "note": "Dostępność poleceń nie potwierdza poprawnej konfiguracji ani dostępu Termux:API."}
