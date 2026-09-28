"""Ograniczony czasowo odczyt zdarzeń Windows FileSystemWatcher."""

import base64
import json
import os
from pathlib import Path, PureWindowsPath
import subprocess
from threading import Event, Lock


_SCRIPT = r'''
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$watcher=[IO.FileSystemWatcher]::new('ROOT')
$watcher.IncludeSubdirectories=$true
$watcher.InternalBufferSize=65536
$watcher.NotifyFilter=[IO.NotifyFilters]'FileName,DirectoryName,LastWrite,Size,Attributes,Security'
$prefix='Prestige-'+[guid]::NewGuid().ToString('N')
$rows=[Collections.Generic.List[object]]::new();$overflow=$false
try {
 foreach($kind in @('Created','Changed','Deleted','Renamed','Error')) {
  Register-ObjectEvent -InputObject $watcher -EventName $kind -SourceIdentifier ($prefix+'-'+$kind)|Out-Null
 }
 $watcher.EnableRaisingEvents=$true
 $until=[DateTime]::UtcNow.AddSeconds(DURATION)
 while([DateTime]::UtcNow -lt $until) {
  foreach($event in @(Get-Event | Where-Object {$_.SourceIdentifier.StartsWith($prefix)})) {
   $kind=$event.SourceIdentifier.Substring($prefix.Length+1)
   if($kind -eq 'Error') {$overflow=$true}
   elseif($rows.Count -lt 100000) {
    $argument=$event.SourceEventArgs
    $rows.Add([pscustomobject]@{kind=$kind;path=$argument.Name;old_path=$(if($kind -eq 'Renamed'){$argument.OldName}else{$null});timestamp=$event.TimeGenerated.ToUniversalTime().ToString('o')})
   } else {$overflow=$true}
   Remove-Event -EventIdentifier $event.EventIdentifier
  }
  Start-Sleep -Milliseconds 20
 }
} finally {
 $watcher.EnableRaisingEvents=$false
 foreach($kind in @('Created','Changed','Deleted','Renamed','Error')) {
  Unregister-Event -SourceIdentifier ($prefix+'-'+$kind) -ErrorAction SilentlyContinue
 }
 $watcher.Dispose()
}
[pscustomobject]@{events=@($rows);overflow=$overflow}|ConvertTo-Json -Depth 5 -Compress
'''

_KINDS = {"Created": "Nowy", "Changed": "Zmieniony", "Deleted": "Usunięty",
          "Renamed": "Zmieniono nazwę"}

_STREAM_SCRIPT = r'''
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$watcher=[IO.FileSystemWatcher]::new('ROOT')
$watcher.IncludeSubdirectories=$true
$watcher.InternalBufferSize=65536
$watcher.NotifyFilter=[IO.NotifyFilters]'FileName,DirectoryName,LastWrite,Size,Attributes,Security'
$prefix='Prestige-'+[guid]::NewGuid().ToString('N')
try {
 foreach($kind in @('Created','Changed','Deleted','Renamed','Error')) {
  Register-ObjectEvent -InputObject $watcher -EventName $kind -SourceIdentifier ($prefix+'-'+$kind)|Out-Null
 }
 $watcher.EnableRaisingEvents=$true
 [Console]::Out.WriteLine('{"ready":true}')
 [Console]::Out.Flush()
 while($true) {
  $rows=[Collections.Generic.List[object]]::new();$overflow=$false
  foreach($event in @(Get-Event | Where-Object {$_.SourceIdentifier.StartsWith($prefix)})) {
   $kind=$event.SourceIdentifier.Substring($prefix.Length+1)
   if($kind -eq 'Error') {$overflow=$true}
   elseif($rows.Count -lt 10000) {
    $argument=$event.SourceEventArgs
    $rows.Add([pscustomobject]@{kind=$kind;path=$argument.Name;old_path=$(if($kind -eq 'Renamed'){$argument.OldName}else{$null});timestamp=$event.TimeGenerated.ToUniversalTime().ToString('o')})
   } else {$overflow=$true}
   Remove-Event -EventIdentifier $event.EventIdentifier
  }
  if($rows.Count -gt 0 -or $overflow) {
   $line=[pscustomobject]@{events=@($rows);overflow=$overflow}|ConvertTo-Json -Depth 5 -Compress
   [Console]::Out.WriteLine($line)
   [Console]::Out.Flush()
  }
  if($overflow) {break}
  Start-Sleep -Milliseconds 100
 }
} finally {
 $watcher.EnableRaisingEvents=$false
 foreach($kind in @('Created','Changed','Deleted','Renamed','Error')) {
  Unregister-Event -SourceIdentifier ($prefix+'-'+$kind) -ErrorAction SilentlyContinue
 }
 $watcher.Dispose()
}
'''


def _relative(value):
    if not isinstance(value, str) or not value:
        raise ValueError("Zdarzenie ma pustą ścieżkę.")
    path = PureWindowsPath(value)
    if path.is_absolute() or path.drive or any(part in {"..", "."} for part in path.parts):
        raise ValueError("Zdarzenie ma ścieżkę poza obserwowanym katalogiem.")
    return path.as_posix()


def normalize_native_capture(payload):
    if not isinstance(payload, dict) or type(payload.get("overflow")) is not bool:
        raise ValueError("Nieprawidłowa odpowiedź FileSystemWatcher.")
    if payload["overflow"]:
        return {"status": "UNKNOWN", "reason": "Przepełnienie bufora zdarzeń.", "events": []}
    rows = payload.get("events")
    if not isinstance(rows, list):
        raise ValueError("Nieprawidłowa lista zdarzeń FileSystemWatcher.")
    events = []
    for row in rows:
        if not isinstance(row, dict) or row.get("kind") not in _KINDS:
            continue
        event = {"kind": _KINDS[row["kind"]], "path": _relative(row.get("path")),
                 "at_utc": str(row.get("timestamp") or "")}
        if row["kind"] == "Renamed":
            event["old_path"] = _relative(row.get("old_path"))
        if not event["at_utc"]:
            raise ValueError("Brak czasu zdarzenia FileSystemWatcher.")
        events.append(event)
    return {"status": "COMPLETE", "events": events}


def collect_native_events(root, duration=10.0, *, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        raise ValueError("Natywne zdarzenia wymagają Windows.")
    path = Path(root)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("Wymagany rzeczywisty katalog źródłowy.")
    path = path.resolve()
    if not 0.1 <= duration <= 3600:
        raise ValueError("Czas odczytu musi mieścić się w zakresie 0,1–3600 s.")
    script = _SCRIPT.replace("ROOT", str(path).replace("'", "''")).replace("DURATION", str(float(duration)))
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    completed = runner(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                       capture_output=True, text=True, encoding="utf-8",
                       timeout=duration + 30, check=False)
    if completed.returncode:
        raise RuntimeError((completed.stderr or "FileSystemWatcher zakończył się błędem.").strip())
    try:
        payload = json.loads(completed.stdout.lstrip("\ufeff"))
    except json.JSONDecodeError as error:
        raise ValueError("FileSystemWatcher nie zwrócił poprawnego JSON.") from error
    return normalize_native_capture(payload)


class NativeEventStream:
    """Jeden proces i jeden FileSystemWatcher aż do jawnego zatrzymania."""

    def __init__(self, root, *, launcher=subprocess.Popen, platform=None):
        if (platform or os.name) != "nt":
            raise ValueError("Natywne zdarzenia wymagają Windows.")
        path = Path(root)
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Wymagany rzeczywisty katalog źródłowy.")
        self.root = path.resolve()
        self.launcher = launcher
        self.process = None
        self.lock = Lock()
        self.ready = Event()
        self.stopping = False

    def watch(self, on_batch, *, on_ready=None):
        script = _STREAM_SCRIPT.replace("ROOT", str(self.root).replace("'", "''"))
        encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
        process = self.launcher(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", bufsize=1,
        )
        with self.lock:
            self.process = process
            if self.stopping:
                process.terminate()
        try:
            first = process.stdout.readline()
            if self.stopping:
                return
            if not first or json.loads(first.lstrip("\ufeff")) != {"ready": True}:
                raise RuntimeError("FileSystemWatcher nie potwierdził uruchomienia.")
            if on_ready is not None:
                on_ready()
            self.ready.set()
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                result = normalize_native_capture(json.loads(line))
                on_batch(result)
                if result["status"] != "COMPLETE":
                    raise RuntimeError(result["reason"])
            if not self.stopping:
                raise RuntimeError("FileSystemWatcher zakończył się niespodziewanie.")
        finally:
            self.stop()
            try:
                process.wait(timeout=5)
            finally:
                process.stdout.close()
                process.stderr.close()

    def stop(self):
        with self.lock:
            self.stopping = True
            process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
