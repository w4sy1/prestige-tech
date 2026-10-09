"""Jawny harmonogram Windows dla odczytowego skanu własnej podsieci."""

from pathlib import Path
import re
import subprocess
import sys

from .daily_schedule import _literal, _run_script
from .network_watch import _read, default_directory, make_profile


TASK_NAME = "PrestigeTech Network Watch"
ROOT = Path(__file__).resolve().parent.parent


def schedule_plan(directory=None, *, time="03:00", python=None, root=None):
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", time):
        raise ValueError("Godzina musi mieć format GG:MM.")
    folder = Path(directory or default_directory()).resolve(strict=True)
    profile = _read(folder / "profile.json")
    if profile != make_profile(profile["scope"], profile["local_ip"], profile["interface_index"]):
        raise ValueError("Nieprawidłowy profil sieci.")
    executable = Path(python or sys.executable).resolve(strict=True)
    workspace = Path(root or ROOT).resolve(strict=True)
    if not (workspace / "prestige_core" / "network_watch.py").is_file():
        raise ValueError("Brak kodu monitoringu.")
    args = subprocess.list2cmdline(["-m", "prestige_core.network_watch", "run",
                                    "--directory", str(folder)])
    return {"task_name": TASK_NAME, "time": time, "python": str(executable),
            "working_directory": str(workspace), "directory": str(folder),
            "arguments": args, "automatic_blocking": False,
            "requires_logged_in_user": True}


def install(plan, *, runner=subprocess.run, platform=None):
    expected = schedule_plan(plan.get("directory"), time=plan.get("time", ""),
                             python=plan.get("python"), root=plan.get("working_directory"))
    if plan != expected:
        raise ValueError("Plan harmonogramu został zmieniony.")
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
    return {"status": "REGISTERED", "task_name": TASK_NAME}


def remove(*, runner=subprocess.run, platform=None):
    _run_script(f"Unregister-ScheduledTask -TaskName {_literal(TASK_NAME)} -Confirm:$false",
                runner=runner, platform=platform)
    return {"status": "REMOVED", "task_name": TASK_NAME}
