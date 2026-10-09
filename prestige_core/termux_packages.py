"""Odczytowe porównanie profilu Setup z lokalną bazą dpkg Termuxa."""

import os

from .termux_setup import PROFILES
from .termux_runtime import run


def compare_profile_packages(profile, *, runner=run, environ=None):
    if profile not in PROFILES:
        raise ValueError("Nieznany profil Termux Setup.")
    env = os.environ if environ is None else environ
    if "com.termux" not in env.get("PREFIX", ""):
        raise RuntimeError("Porównanie pakietów wymaga lokalnego Termuxa.")
    output = runner(["dpkg-query", "-W", "-f=${binary:Package}\n"], timeout=30)
    installed = {line.strip() for line in output.splitlines() if line.strip()}
    requested = set(PROFILES[profile])
    return {"profile": profile, "status": "COMPARED",
            "installed": sorted(requested & installed),
            "missing": sorted(requested - installed),
            "note": "Obecność pakietu nie potwierdza działania narzędzia ani Termux:API."}
