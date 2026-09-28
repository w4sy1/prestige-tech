"""Zbuduj samodzielny Windows EXE pierwszego wycinka Network Center."""

from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def main():
    if os.name != "nt":
        raise SystemExit("EXE buduj na Windows.")
    command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
               "--onefile", "--windowed", "--name", "prestige-network-center",
               "--add-data", str(ROOT / "prestige_core" / "assets" / "DejaVuSans.ttf") + ";.",
               "--distpath", str(ROOT.parent / "tmp" / "network-center-build"),
               "--workpath", str(ROOT.parent / "tmp" / "network-center-work"),
               "--specpath", str(ROOT.parent / "tmp"),
               str(ROOT / "network_center.py")]
    subprocess.run(command, cwd=ROOT, check=True)
    destination = ROOT.parent / "tmp" / "network-center-build"
    shutil.copy2(ROOT / "LICENSE", destination / "LICENSE")
    shutil.copy2(ROOT / "prestige_core" / "assets" / "FONT-LICENSE.txt", destination / "FONT-LICENSE.txt")
    print(destination / "prestige-network-center.exe")


if __name__ == "__main__":
    main()
