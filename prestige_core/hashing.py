"""Jednoprzebiegowe hashowanie pliku dla nowych centrów."""

from pathlib import Path
import hashlib


class FileHashService:
    ALGORITHMS = frozenset(("sha256", "sha512", "sha1", "md5"))

    @classmethod
    def hashes(cls, path, algorithms=("sha256",)):
        algorithms = tuple(algorithms)
        if not algorithms or len(set(algorithms)) != len(algorithms):
            raise ValueError("Wybierz niepowtarzające się algorytmy.")
        if any(name not in cls.ALGORITHMS for name in algorithms):
            raise ValueError("Nieobsługiwany algorytm.")

        path = Path(path)
        if path.is_symlink() or not path.is_file():
            raise ValueError("Wymagany zwykły plik.")
        before = path.stat()
        digests = {name: hashlib.new(name) for name in algorithms}
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                for digest in digests.values():
                    digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("Plik zmienił się podczas odczytu.")
        return {name: digest.hexdigest() for name, digest in digests.items()}

    @classmethod
    def sha256(cls, path):
        return cls.hashes(path)["sha256"]
