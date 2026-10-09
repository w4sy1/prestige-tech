"""Buduj samodzielne EXE Centrów z aktualnego kodu."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
CENTERS = {
    "network": "network_center.py",
    "monitor": "monitor.py",
    "registry": "registry_manager.py",
    "storage": "storage_center.py",
    "android": "android_center.py",
    "security": "security_center.py",
    "system": "system_center.py",
    "termux": "termux_center_gui.py",
    "ai": "ai_center.py",
    "report": "report_center.py",
}


def build(name: str) -> Path:
    if os.name != "nt":
        raise RuntimeError("EXE buduje się na Windows.")
    source = ROOT / CENTERS[name]
    output_name = f"{name}_center" if name not in {"monitor", "registry"} else {
        "monitor": "monitor", "registry": "registry_manager"
    }[name]
    spec_dir = ROOT / "build" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec = spec_dir / f"{output_name}.spec"
    assets = ROOT / "prestige_core" / "assets"
    icon = ROOT.parent / "prestige-tech-dashboard" / "assets" / "prestige_tech_app.ico"
    spec.write_text(
        "# -*- mode: python ; coding: utf-8 -*-\n"
        f"a = Analysis([{str(source)!r}], pathex={[str(ROOT)]!r}, binaries=[], "
        f"datas={[(str(assets), 'prestige_core/assets')]!r}, hiddenimports=[], "
        "hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], "
        "noarchive=False, optimize=0)\n"
        "a.binaries = [item for item in a.binaries if item[0].lower() != 'icuuc.dll']\n"
        "pyz = PYZ(a.pure)\n"
        f"exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name={output_name!r}, "
        "debug=False, bootloader_ignore_signals=False, strip=False, upx=True, "
        "runtime_tmpdir=None, console=False, disable_windowed_traceback=False, "
        "argv_emulation=False, target_arch=None, codesign_identity=None, entitlements_file=None, "
        f"icon={[str(icon)]!r} if {icon.exists()!r} else None)\n",
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--distpath", str(ROOT / "dist" / "centers"),
         "--workpath", str(ROOT / "build" / "pyinstaller" / output_name), str(spec)],
        cwd=ROOT, check=True,
    )
    return ROOT / "dist" / "centers" / f"{output_name}.exe"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("centers", nargs="+", choices=[*CENTERS, "all"])
    args = parser.parse_args()
    names = list(CENTERS) if "all" in args.centers else args.centers
    for name in names:
        path = build(name)
        print(path, flush=True)


if __name__ == "__main__":
    main()
