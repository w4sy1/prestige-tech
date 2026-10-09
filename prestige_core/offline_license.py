"""Weryfikacja podpisanej licencji PRO offline; klucz prywatny nie trafia do aplikacji."""

import base64
from datetime import date
import json
from pathlib import Path
import os


DOMAIN = b"PrestigeTech-Pro-License-v1\0"


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_license(path, public_key_pem, *, today=None):
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as error:
        raise RuntimeError("Licencja PRO wymaga pakietu cryptography.") from error
    license_path = Path(path)
    if license_path.is_symlink() or not license_path.is_file() or license_path.stat().st_size > 16_384:
        raise ValueError("Wymagany zwykły plik licencji do 16 KiB.")
    record = json.loads(license_path.read_text(encoding="utf-8-sig"))
    if not isinstance(record, dict) or set(record) != {"payload", "signature"}:
        raise ValueError("Nieprawidłowy format licencji.")
    payload = record["payload"]
    if (not isinstance(payload, dict) or set(payload) != {"schema_version", "edition", "license_id", "expires"}
            or type(payload["schema_version"]) is not int or payload["schema_version"] != 1
            or payload["edition"] != "PRO" or not isinstance(payload["license_id"], str)
            or not 8 <= len(payload["license_id"]) <= 100 or not isinstance(payload["expires"], str)):
        raise ValueError("Nieprawidłowe dane licencji PRO.")
    try:
        expiry = date.fromisoformat(payload["expires"])
        key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise ValueError("Wymagany klucz publiczny Ed25519.")
        signature = base64.b64decode(record["signature"], validate=True)
        key.verify(signature, DOMAIN + _canonical(payload))
    except (InvalidSignature, ValueError, TypeError) as error:
        raise ValueError("Podpis lub data licencji PRO są nieprawidłowe.") from error
    if expiry < (today or date.today()):
        raise ValueError("Licencja PRO wygasła.")
    return {"edition": "PRO", "license_id": payload["license_id"], "expires": expiry.isoformat()}


def create_issuer_keys(private_path, public_path, password):
    """Klucz prywatny zapisz poza repo, szyfrowany hasłem podanym lokalnie."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(password, str) or len(password.encode("utf-8")) < 12:
        raise ValueError("Hasło klucza wydawcy musi mieć co najmniej 12 bajtów.")
    private_path, public_path = Path(private_path), Path(public_path)
    if private_path.exists() or public_path.exists() or private_path.resolve() == public_path.resolve():
        raise FileExistsError("Wskaż dwie różne nowe ścieżki kluczy.")
    private = Ed25519PrivateKey.generate()
    secret = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                   serialization.BestAvailableEncryption(password.encode("utf-8")))
    public = private.public_key().public_bytes(serialization.Encoding.PEM,
                                                 serialization.PublicFormat.SubjectPublicKeyInfo)
    with os.fdopen(os.open(private_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as stream:
        stream.write(secret)
    try:
        with public_path.open("xb") as stream:
            stream.write(public)
    except BaseException:
        private_path.unlink(missing_ok=True)
        raise
    return {"private_key": str(private_path), "public_key": str(public_path)}


def issue_license(private_path, password, license_id, expires, destination):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(license_id, str) or not 8 <= len(license_id) <= 100:
        raise ValueError("Identyfikator licencji musi mieć 8–100 znaków.")
    date.fromisoformat(expires)
    private = serialization.load_pem_private_key(Path(private_path).read_bytes(),
                                                 password=password.encode("utf-8"))
    if not isinstance(private, Ed25519PrivateKey):
        raise ValueError("Wymagany klucz wydawcy Ed25519.")
    payload = {"schema_version": 1, "edition": "PRO", "license_id": license_id,
               "expires": expires}
    record = {"payload": payload,
              "signature": base64.b64encode(private.sign(DOMAIN + _canonical(payload))).decode("ascii")}
    with Path(destination).open("x", encoding="utf-8") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"license_id": license_id, "expires": expires, "file": str(destination)}
