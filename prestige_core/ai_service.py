"""Wspólna analiza raportów Centrów; sieć tylko po jawnym wywołaniu external()."""

from .ai_normalization import normalize
from .ai_providers import LocalProvider
from .ai_remote import analyze as remote_analyze, payload
from .security_check import load_evidence


def metrics_from_file(path):
    return normalize(load_evidence(path))


def local(path):
    return LocalProvider().analyze(metrics_from_file(path))


def preview(path, model):
    metrics = metrics_from_file(path)
    return {"data_leaves_device": False, "preview": payload(metrics, model),
            "note": "To jest dokładne żądanie do API; podgląd niczego nie wysyła."}


def external(path, model, *, expected_payload=None, analyzer=remote_analyze):
    metrics = metrics_from_file(path)
    if expected_payload is not None and payload(metrics, model) != expected_payload:
        raise ValueError("Raport lub model zmienił się od podglądu. Obejrzyj dane ponownie.")
    return analyzer(metrics, model)
