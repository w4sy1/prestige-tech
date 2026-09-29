"""Odczytowa analiza pliku przeniesiona z File Inspector do Security Center."""

from collections import Counter
import hashlib
import math
import mimetypes
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

MAGIC = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"%PDF-", "application/pdf"),
         (b"PK\x03\x04", "application/zip"),
         (b"MZ", "application/vnd.microsoft.portable-executable"))


def _signature(path, *, runner=subprocess.run, platform=None):
    if (platform or os.name) != "nt":
        return {"status": "UNAVAILABLE"}
    script = ("$ErrorActionPreference='Stop';"
              f"$s=Get-AuthenticodeSignature -LiteralPath '{str(path).replace(chr(39), chr(39) * 2)}';"
              "[pscustomobject]@{status=[string]$s.Status;publisher=$s.SignerCertificate.Subject} | ConvertTo-Json -Compress")
    try:
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if not executable:
            return {"status": "UNKNOWN"}
        result = runner([executable, "-NoProfile", "-NonInteractive", "-Command", script],
                        capture_output=True, text=True, encoding="utf-8", timeout=30, check=False)
        if result.returncode:
            return {"status": "UNKNOWN"}
        import json
        row = json.loads(result.stdout.lstrip("\ufeff"))
        return row if isinstance(row, dict) else {"status": "UNKNOWN"}
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"status": "UNKNOWN"}


def inspect_file(path, *, include_strings=False, runner=subprocess.run, platform=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("Wymagany zwykły plik.")
    path = path.resolve(strict=True)
    before = path.stat()
    counts = Counter()
    sample = bytearray()
    digests = {name: hashlib.new(name) for name in ("sha256", "sha512", "sha1", "md5")}
    with path.open("rb") as stream:
        head = stream.read(64)
        stream.seek(0)
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            counts.update(chunk)
            for digest in digests.values():
                digest.update(chunk)
            if include_strings and len(sample) < 1024 * 1024:
                sample.extend(chunk[:1024 * 1024 - len(sample)])
        pe = None
        if head.startswith(b"MZ") and len(head) >= 64:
            offset = struct.unpack_from("<I", head, 60)[0]
            if offset <= before.st_size - 24:
                stream.seek(offset)
                header = stream.read(24)
                if header[:4] == b"PE\0\0":
                    machine, sections, timestamp = struct.unpack_from("<HHI", header, 4)
                    pe = {"machine": hex(machine), "sections": sections, "timestamp": timestamp}
    hashes = {name: digest.hexdigest() for name, digest in digests.items()}
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("Plik zmienił się podczas analizy.")
    entropy = (-sum((n / before.st_size) * math.log2(n / before.st_size)
                    for n in counts.values()) if before.st_size else 0.0)
    magic = next((mime for prefix, mime in MAGIC if head.startswith(prefix)), "unknown")
    strings = ([match.decode("ascii") for match in re.findall(rb"[\x20-\x7e]{6,}", sample)[:100]]
               if include_strings else [])
    return {"path": str(path), "name": path.name, "extension": path.suffix,
            "mime_by_extension": mimetypes.guess_type(path.name)[0], "mime_by_magic": magic,
            "size": before.st_size, "modified_timestamp": before.st_mtime,
            "created_timestamp": getattr(before, "st_birthtime", before.st_ctime if os.name == "nt" else None),
            "hashes": hashes, "entropy_bits_per_byte": entropy,
            "signature": _signature(path, runner=runner, platform=platform), "pe": pe,
            "strings": strings, "strings_sampled_bytes": len(sample),
            "note": "SHA1/MD5 wyłącznie dla kompatybilności. Entropia i brak podpisu nie dowodzą malware."}
