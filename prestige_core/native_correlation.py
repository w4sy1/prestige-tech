"""Korelacja zdarzeń FileSystemWatcher z pełnymi migawkami ACL/ADS."""

from .file_extended import metadata_complete


def correlate_extended(native_result, before, after):
    if native_result.get("status") != "COMPLETE":
        return native_result
    if (not before.get("complete") or not after.get("complete")
            or not before.get("options", {}).get("extended")
            or not after.get("options", {}).get("extended")
            or before.get("root") != after.get("root")):
        return {"status": "UNKNOWN", "reason": "Niepełny odczyt ACL/ADS przy zdarzeniu natywnym.",
                "events": []}
    old = {row["path"].replace("\\", "/"): row for row in before["files"]}
    new = {row["path"].replace("\\", "/"): row for row in after["files"]}
    events = []
    for item in native_result["events"]:
        event = dict(item)
        left, right = old.get(item["path"]), new.get(item["path"])
        if left is not None and right is not None:
            a, b = left.get("extended"), right.get("extended")
            if not metadata_complete(a) or not metadata_complete(b):
                return {"status": "UNKNOWN", "reason": "Niepełna para metadanych ACL/ADS.",
                        "events": []}
            changes = []
            if (a.get("sddl"), a.get("mode")) != (b.get("sddl"), b.get("mode")):
                changes.append("ACL")
            if a.get("streams") != b.get("streams"):
                changes.append("ADS")
            if left.get("sha256") != right.get("sha256"):
                changes.append("treść")
            if changes:
                event["changes"] = changes
        events.append(event)
    return {"status": "COMPLETE", "events": events}
