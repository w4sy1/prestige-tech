"""Testowy silnik RAW dla zwykłych plików; nie otwiera fizycznych dysków."""

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


def image_fixture_file(source, destination, *, cancel_event=None, chunk_size=1024 * 1024):
    """Skopiuj zwykły plik do nowego .img; zachowaj INCOMPLETE po błędzie."""
    source = Path(source)
    destination = Path(destination)
    metadata_path = Path(str(destination) + ".json")
    if chunk_size < 4096 or chunk_size > 16 * 1024 * 1024:
        raise ValueError("Niedozwolony rozmiar bufora.")
    if source.is_symlink() or not source.is_file():
        raise ValueError("Tryb fixture wymaga zwykłego pliku źródłowego.")
    if destination.suffix.lower() != ".img":
        raise ValueError("Wymagane rozszerzenie .img.")
    if source.resolve() == destination.resolve():
        raise ValueError("Cel nie może być źródłem.")
    if destination.exists() or metadata_path.exists():
        raise FileExistsError("Obraz lub jego metadane już istnieją.")
    before = source.stat()
    metadata = {
        "schema_version": 1, "mode": "fixture_regular_file",
        "source_name": source.name, "expected_bytes": before.st_size,
        "read_bytes": 0, "status": "INCOMPLETE", "sha256_image": None,
        "verified_image": False, "started_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    digest = hashlib.sha256()
    failure = None
    try:
        with source.open("rb") as input_stream, destination.open("xb") as output_stream:
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    failure = "Przerwano na żądanie użytkownika."
                    break
                block = input_stream.read(chunk_size)
                if not block:
                    break
                output_stream.write(block)
                digest.update(block)
                metadata["read_bytes"] += len(block)
            output_stream.flush()
            os.fsync(output_stream.fileno())
        after = source.stat()
        if failure is None and (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            failure = "Źródło zmieniło się podczas odczytu."
        if failure is None and metadata["read_bytes"] != before.st_size:
            failure = "Odczytano mniej bajtów niż oczekiwano."
        metadata["sha256_image"] = digest.hexdigest()
        if failure is None:
            verify = hashlib.sha256()
            with destination.open("rb") as check_stream:
                for block in iter(lambda: check_stream.read(chunk_size), b""):
                    verify.update(block)
            metadata["verified_image"] = verify.hexdigest() == metadata["sha256_image"]
            if not metadata["verified_image"]:
                failure = "Ponowny odczyt obrazu wykazał niezgodność SHA-256."
    except FileExistsError:
        raise
    except OSError as error:
        failure = f"Błąd I/O: {error}"
    metadata["status"] = "INCOMPLETE" if failure else "COMPLETE"
    metadata["error"] = failure
    metadata["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return metadata
