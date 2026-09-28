"""Odczyt bezpośrednich wartości z lokalnych szablonów zasad Microsoft ADMX."""

from pathlib import Path
import re
import xml.etree.ElementTree as ET

from .registry_read import ReadOperation, OPERATIONS as CURATED


_DECLARATION = re.compile(r"^\s*<\?xml[^>]*\?>")


def load_admx_catalog(directory, *, max_files=500, max_bytes=2_000_000):
    root = Path(directory)
    if not root.is_dir():
        raise ValueError("Katalog PolicyDefinitions nie istnieje.")
    files = sorted(root.glob("*.admx"), key=lambda item: item.name.casefold())
    if len(files) > max_files:
        raise ValueError("Zbyt wiele szablonów ADMX.")
    used = {(item.hive, item.key.casefold(), item.values[0].casefold())
            for item in CURATED if item.values and len(item.values) == 1}
    operations = []
    errors = []
    for file in files:
        try:
            if file.stat().st_size > max_bytes:
                raise ValueError("Szablon przekracza limit rozmiaru.")
            raw = file.read_bytes()
            source = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff"))
                                else "utf-8-sig")
            source = _DECLARATION.sub("", source, count=1)
            document = ET.fromstring(source)
            for policy in document.iter():
                if policy.tag.rsplit("}", 1)[-1] != "policy":
                    continue
                policy_class = policy.get("class")
                if policy_class not in ("User", "Machine", "Both"):
                    continue
                hive = {"User": "HKCU", "Machine": "HKLM", "Both": "BOTH"}[policy_class]
                key, value = policy.get("key"), policy.get("valueName")
                if not key or not value or not key.casefold().startswith("software\\"):
                    continue
                identity = (hive, key.casefold(), value.casefold())
                if identity in used:
                    continue
                used.add(identity)
                name = policy.get("name") or value
                operations.append(ReadOperation(
                    f"REG-ADMX-{len(operations) + 1:04d}", name, "Zasady ADMX",
                    "Odczytaj pojedynczą wartość zasady z lokalnego szablonu Microsoft; brak oznacza nieustawioną zasadę.",
                    hive, key, (value,), str(file.resolve()),
                ))
        except (OSError, UnicodeError, ET.ParseError, ValueError) as error:
            errors.append({"file": file.name, "error": type(error).__name__})
    return {"operations": tuple(operations), "templates": len(files),
            "errors": errors, "status": "UNKNOWN" if errors else "COMPLETE"}
