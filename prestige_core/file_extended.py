"""Dodatkowe dowody integralności: ACL i ADS Windows albo tryb POSIX."""

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")


def metadata_complete(row):
    if not isinstance(row, dict) or row.get("acl_status") not in {"OK", "POSIX_MODE_ONLY"}:
        return False
    if row["acl_status"] == "OK" and (not isinstance(row.get("sddl"), str) or not row["sddl"]):
        return False
    if row["acl_status"] == "POSIX_MODE_ONLY" and (not isinstance(row.get("mode"), str) or not row["mode"]):
        return False
    if row.get("ads_status") not in {"OK", "NOT_APPLICABLE"}:
        return False
    streams = row.get("streams", [])
    return isinstance(streams, list) and all(
        isinstance(stream, dict) and isinstance(stream.get("name"), str)
        and type(stream.get("size")) is int and stream["size"] >= 0
        and isinstance(stream.get("sha256"), str) and _HASH.fullmatch(stream["sha256"])
        for stream in streams
    )


def collect_extended(root, names, *, runner=subprocess.run, platform=None):
    root = Path(root).resolve(strict=True)
    names = list(names)
    if (platform or os.name) != "nt":
        result = {}
        for name in names:
            mode = (root / name).stat(follow_symlinks=False).st_mode & 0o7777
            result[name] = {"mode": oct(mode), "acl_status": "POSIX_MODE_ONLY",
                            "ads_status": "NOT_APPLICABLE", "streams": []}
        return result
    result = {}
    for start in range(0, len(names), 100):
        batch = names[start:start + 100]
        quoted = ",".join("'" + name.replace("'", "''") + "'" for name in batch)
        script = r'''
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$root='ROOT';$r=[ordered]@{}
foreach($relative in @(NAMES)) {
 $file=Join-Path $root $relative;$row=[ordered]@{}
 try {$acl=[IO.File]::GetAccessControl($file);$row.sddl=$acl.GetSecurityDescriptorSddlForm([Security.AccessControl.AccessControlSections]::All);$row.acl_status='OK'}
 catch {$row.acl_status='UNKNOWN';$row.acl_error_type=$_.Exception.GetType().Name}
 try {
  $row.streams=@(Get-Item -LiteralPath $file -Stream * |
   Where-Object Stream -ne ':$DATA' | ForEach-Object {
    $hash=$null
    [pscustomobject]@{name=$_.Stream;size=$_.Length;sha256=$hash}
   } | Sort-Object name)
  $row.ads_status='OK'
 } catch {$row.ads_status='UNKNOWN'}
 $r[$relative]=$row
}
$r|ConvertTo-Json -Depth 6 -Compress
'''.replace("ROOT", str(root).replace("'", "''")).replace("NAMES", quoted)
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        completed = runner(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            capture_output=True, text=True, encoding="utf-8", timeout=120, check=False,
        )
        if completed.returncode:
            raise RuntimeError((completed.stderr or "Nie odczytano ACL/ADS.").strip())
        payload = json.loads(completed.stdout.lstrip("\ufeff"))
        if not isinstance(payload, dict):
            raise ValueError("Nieprawidłowe metadane ACL/ADS.")
        for name, row in payload.items():
            for stream in row.get("streams", []):
                try:
                    digest = hashlib.sha256()
                    with open(str(root / name) + ":" + stream["name"], "rb") as source:
                        for chunk in iter(lambda: source.read(1024 * 1024), b""):
                            digest.update(chunk)
                    stream["sha256"] = digest.hexdigest()
                except (OSError, KeyError, TypeError):
                    stream["sha256"] = None
        result.update(payload)
    return result
