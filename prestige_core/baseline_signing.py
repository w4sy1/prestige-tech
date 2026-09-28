"""Podpis odłączony Ed25519 dla pliku baseline; klucz publiczny podaje użytkownik."""

import base64
import hashlib
import json
import os
from pathlib import Path


_DOMAIN = b"PrestigeTech-manifest-v1\0"


def _crypto():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as error:
        raise RuntimeError("Podpisy wymagają pakietu cryptography.") from error
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey


def _digest(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.digest()


def new_key(private_path, public_path, password):
    _, serialization, Private, _ = _crypto()
    private_path, public_path = Path(private_path), Path(public_path)
    password = password.encode("utf-8") if isinstance(password, str) else password
    if not isinstance(password, bytes) or len(password) < 12:
        raise ValueError("Hasło klucza musi mieć co najmniej 12 bajtów UTF-8.")
    if private_path.resolve() == public_path.resolve() or private_path.exists() or public_path.exists():
        raise ValueError("Wskaż dwa różne, nowe pliki kluczy.")
    key = Private.generate()
    private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.BestAvailableEncryption(password))
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                            serialization.PublicFormat.SubjectPublicKeyInfo)
    with os.fdopen(os.open(private_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
        stream.write(private)
    try:
        with public_path.open("xb") as stream:
            stream.write(public)
    except BaseException:
        private_path.unlink(missing_ok=True)
        raise
    return {"private_key": str(private_path), "public_key": str(public_path)}


def sign(file, key_path, signature_path, password):
    _, serialization, Private, _ = _crypto()
    password = password.encode("utf-8") if isinstance(password, str) else password
    key = serialization.load_pem_private_key(Path(key_path).read_bytes(), password=password)
    if not isinstance(key, Private):
        raise ValueError("Wymagany klucz Ed25519.")
    digest = _digest(file)
    record = {"schema_version": 1, "algorithm": "Ed25519-SHA256", "sha256": digest.hex(),
              "signature": base64.b64encode(key.sign(_DOMAIN + digest)).decode("ascii")}
    with Path(signature_path).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False)
        stream.write("\n")
    return {"signed": True, "signature_file": str(signature_path)}


def verify(file, public_path, signature_path):
    InvalidSignature, serialization, _, Public = _crypto()
    record = json.loads(Path(signature_path).read_text(encoding="utf-8"))
    if not isinstance(record, dict) or record.get("schema_version") != 1 or record.get("algorithm") != "Ed25519-SHA256":
        raise ValueError("Nieobsługiwany podpis.")
    key = serialization.load_pem_public_key(Path(public_path).read_bytes())
    if not isinstance(key, Public):
        raise ValueError("Wymagany klucz publiczny Ed25519.")
    digest = _digest(file)
    if digest.hex() != record.get("sha256"):
        return {"ok": False, "reason": "Zmieniono treść pliku."}
    try:
        signature = base64.b64decode(record["signature"], validate=True)
        key.verify(signature, _DOMAIN + digest)
    except (InvalidSignature, ValueError, KeyError, TypeError):
        return {"ok": False, "reason": "Podpis nie pasuje do podanego klucza."}
    return {"ok": True, "algorithm": "Ed25519-SHA256",
            "note": "Weryfikacja dotyczy podanego klucza, nie tożsamości jego właściciela."}
