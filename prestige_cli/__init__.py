"""Wspólne CLI nowych Centrów i zgodność z 26 niezależnymi narzędziami."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from . import legacy
from prestige_core.ai_service import external, local, preview
from prestige_core.file_inspector import inspect_file
from prestige_core.file_inspector_report import export_file_report


CENTERS = {
    "network": "network_center.py", "monitor": "monitor.py",
    "registry": "registry_manager.py", "storage": "storage_center.py",
    "android": "android_center.py", "security": "security_center.py",
    "system": "system_center.py", "termux": "termux_center_gui.py",
    "ai": "ai_center.py", "report": "report_center.py",
}


def center_script(root, name, arguments=()):
    if name not in CENTERS:
        raise ValueError("Nieznane Centrum.")
    filename = ("termux_center.py" if name == "termux" and arguments
                and arguments[0] in ("setup", "toolkit") else CENTERS[name])
    root = Path(root).resolve()
    script = root / filename
    if script.is_symlink() or not script.is_file():
        raise FileNotFoundError("Brak pliku Centrum: " + filename)
    script.resolve().relative_to(root)
    return script


def main(argv=None, *, runner=subprocess.run):
    parser = argparse.ArgumentParser(description="PRESTIGE TECH — wspólny CLI Centrów")
    parser.add_argument("--centers-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--tools-root", default=os.environ.get(
        "PRESTIGE_TOOLS_ROOT", str(Path(__file__).resolve().parents[2])))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    subcommands = parser.add_subparsers(dest="kind")
    center = subcommands.add_parser("center", help="Uruchom nowe Centrum")
    center.add_argument("name", choices=CENTERS)
    center.add_argument("arguments", nargs=argparse.REMAINDER)
    old = subcommands.add_parser("legacy", help="Uruchom niezależne stare narzędzie")
    old.add_argument("tool", choices=legacy.tools())
    old.add_argument("arguments", nargs=argparse.REMAINDER)
    ai = subcommands.add_parser("ai", help="Analiza raportu JSON")
    ai.add_argument("mode", choices=("local", "preview", "external"))
    ai.add_argument("input")
    ai.add_argument("--model", default="gpt-5-mini")
    ai.add_argument("--send", action="store_true", help="Jawnie wyślij metryki do API")
    file_command = subcommands.add_parser("file", help="Odczytowa inspekcja pliku")
    file_command.add_argument("path")
    file_command.add_argument("--strings", action="store_true", help="Dołącz ciągi znaków, także prywatne")
    file_command.add_argument("--output", help="Katalog raportów JSON/TXT/HTML")
    file_command.add_argument("--pdf", help="Nowa ścieżka raportu PDF")
    args = parser.parse_args(argv)
    try:
        if args.list:
            installed = {}
            for name in legacy.tools():
                try:
                    legacy.resolve(args.tools_root, name)
                except (OSError, ValueError):
                    installed[name] = False
                else:
                    installed[name] = True
            print(json.dumps({"centers": {name: Path(args.centers_root, script).is_file()
                                          for name, script in CENTERS.items()},
                              "legacy": installed}, ensure_ascii=False, indent=2))
            return 0
        if args.kind is None:
            parser.print_help()
            return 0
        if args.kind == "ai":
            if args.dry_run:
                print(json.dumps(preview(args.input, args.model), ensure_ascii=False, indent=2))
                return 0
            if args.mode == "external" and not args.send:
                raise ValueError("Wysyłka wymaga --send. Najpierw użyj trybu preview.")
            if args.mode != "external" and args.send:
                raise ValueError("--send jest tylko dla trybu external.")
            result = (local(args.input) if args.mode == "local" else
                      preview(args.input, args.model) if args.mode == "preview" else
                      external(args.input, args.model))
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
            return 0
        if args.kind == "file":
            if args.dry_run:
                print(json.dumps({"file": args.path, "strings": args.strings,
                                  "output": args.output, "pdf": args.pdf}, ensure_ascii=False))
                return 0
            from datetime import datetime, timezone
            report = {"schema_version": 1, "tool": "Prestige File Inspector",
                      "created_utc": datetime.now(timezone.utc).isoformat(),
                      "data": inspect_file(args.path, include_strings=args.strings)}
            if args.pdf:
                from prestige_core.pdf_export import export_pdf
                export_pdf(report, args.pdf, title="Prestige File Inspector")
            if args.output:
                print(json.dumps({"files": export_file_report(report, args.output)},
                                 ensure_ascii=False))
            else:
                print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
        forwarded = args.arguments[1:] if args.arguments[:1] == ["--"] else args.arguments
        if args.kind == "legacy":
            if not forwarded and args.tool != "prestige-windows-toolkit":
                forwarded = ["--help"]
            script = legacy.resolve(args.tools_root, args.tool)
            if args.dry_run:
                print(json.dumps({"tool": args.tool, "script": str(script),
                                  "arguments": forwarded}, ensure_ascii=False))
                return 0
            return legacy.launch(args.tools_root, args.tool, forwarded)
        script = center_script(args.centers_root, args.name, forwarded)
        command = [sys.executable, str(script), *forwarded]
        if args.dry_run:
            print(json.dumps({"center": args.name, "command": command}, ensure_ascii=False))
            return 0
        return runner(command, shell=False, cwd=str(Path(args.centers_root).resolve())).returncode
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print("Błąd: " + str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
