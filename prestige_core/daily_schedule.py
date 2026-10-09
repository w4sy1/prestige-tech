"""Jawna rejestracja odczytowego przeglądu w Harmonogramie zadań Windows."""

import argparse
import base64
import os
from pathlib import Path
import re
import subprocess
import sys

from .daily_checks import default_report_dir


TASK_NAME = "PrestigeTech Daily Check"
REPO_ROOT = Path(__file__).resolve().parent.parent


def _literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def schedule_plan(time="02:00", *, include_internet=False, python=None, root=None, report_dir=None):
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
        raise ValueError("Godzina musi mieć format GG:MM (00:00–23:59).")
    executable = Path(python or sys.executable).resolve(strict=True)
    workspace = Path(root or REPO_ROOT).resolve(strict=True)
    if not workspace.is_dir() or not (workspace / "prestige_core" / "daily_checks.py").is_file():
        raise ValueError("Nie znaleziono kodu przeglądu w wybranym katalogu.")
    output = Path(report_dir or default_report_dir()).resolve()
    args = ["-m", "prestige_core.daily_checks", "--out", str(output), "--printer", "--audio"]
    if include_internet:
        args.append("--internet")
    return {"task_name": TASK_NAME, "time": time, "python": str(executable),
            "working_directory": str(workspace),
            "arguments": subprocess.list2cmdline(args),
            "report_directory": str(output), "include_internet": include_internet,
            "automatic_repairs": False, "requires_logged_in_user": True}


def _run_script(script, *, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise RuntimeError("Harmonogram jest dostępny tylko na Windows.")
    encoded = base64.b64encode(("$ErrorActionPreference='Stop';" + script).encode("utf-16le")).decode("ascii")
    result = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                    capture_output=True, text=True, timeout=30, check=False)
    if result.returncode:
        raise RuntimeError("Nie udało się zmienić zadania w Harmonogramie Windows.")


def install_daily_schedule(plan, *, runner=subprocess.run, platform=None):
    if plan.get("task_name") != TASK_NAME or plan.get("automatic_repairs") is not False:
        raise ValueError("Nieprawidłowy plan zadania.")
    expected = schedule_plan(plan.get("time", ""),
                             include_internet=plan.get("include_internet") is True,
                             python=plan.get("python"), root=plan.get("working_directory"),
                             report_dir=plan.get("report_directory"))
    if plan != expected:
        raise ValueError("Plan zadania został zmieniony lub jest niekompletny.")
    hour, minute = map(int, plan["time"].split(":"))
    script = (
        f"if (Get-ScheduledTask -TaskName {_literal(TASK_NAME)} -ErrorAction SilentlyContinue) "
        "{ throw 'Zadanie już istnieje.' };"
        f"$action=New-ScheduledTaskAction -Execute {_literal(plan['python'])} "
        f"-Argument {_literal(plan['arguments'])} "
        f"-WorkingDirectory {_literal(plan['working_directory'])};"
        f"$trigger=New-ScheduledTaskTrigger -Daily -At ([datetime]::Today.AddHours({hour}).AddMinutes({minute}));"
        "$principal=New-ScheduledTaskPrincipal "
        "-UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) "
        "-LogonType Interactive -RunLevel Limited;"
        "$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable "
        "-ExecutionTimeLimit (New-TimeSpan -Minutes 5);"
        f"Register-ScheduledTask -TaskName {_literal(TASK_NAME)} -Action $action "
        "-Trigger $trigger -Principal $principal -Settings $settings | Out-Null"
    )
    _run_script(script, runner=runner, platform=platform)
    return {"status": "REGISTERED", "task_name": TASK_NAME, "time": plan["time"]}


def remove_daily_schedule(*, runner=subprocess.run, platform=None):
    _run_script(f"Unregister-ScheduledTask -TaskName {_literal(TASK_NAME)} -Confirm:$false",
                runner=runner, platform=platform)
    return {"status": "REMOVED", "task_name": TASK_NAME}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Harmonogram odczytowego przeglądu Prestige Tech")
    parser.add_argument("action", choices=("plan", "install", "remove"))
    parser.add_argument("--time", default="02:00")
    parser.add_argument("--internet", action="store_true", help="Zewnętrzne sondy sieciowe")
    parser.add_argument("--confirm", action="store_true", help="Potwierdź zmianę zadania Windows")
    args = parser.parse_args(argv)
    if args.action == "remove":
        if not args.confirm:
            parser.error("Usunięcie zadania wymaga --confirm.")
        print(remove_daily_schedule())
        return 0
    plan = schedule_plan(args.time, include_internet=args.internet)
    if args.action == "plan":
        print(plan)
        return 0
    if not args.confirm:
        parser.error("Rejestracja zadania wymaga --confirm.")
    print(install_daily_schedule(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
