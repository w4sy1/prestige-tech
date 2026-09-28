import unittest

from prestige_core.native_correlation import correlate_extended


HASH = "a" * 64


def snapshot(sddl="O:BAG:BAD:(A;;FA;;;SY)", streams=None, complete=True):
    return {"root": "C:/fixture", "complete": complete, "options": {"extended": True},
            "files": [{"path": "sample.txt", "sha256": HASH, "extended": {
                "acl_status": "OK", "sddl": sddl, "ads_status": "OK",
                "streams": streams or []}}]}


class NativeCorrelationTests(unittest.TestCase):
    def test_marks_acl_and_ads_changes_on_native_event(self):
        before = snapshot()
        after = snapshot(sddl="O:BAG:BAD:(A;;FR;;;SY)", streams=[{
            "name": "Zone.Identifier", "size": 4, "sha256": HASH}])
        native = {"status": "COMPLETE", "events": [{"kind": "Zmieniony",
            "path": "sample.txt", "at_utc": "2026-09-28T00:00:00Z"}]}
        result = correlate_extended(native, before, after)
        self.assertEqual(result["events"][0]["changes"], ["ACL", "ADS"])

    def test_incomplete_metadata_is_unknown_not_clean(self):
        native = {"status": "COMPLETE", "events": [{"kind": "Zmieniony",
            "path": "sample.txt", "at_utc": "now"}]}
        self.assertEqual(correlate_extended(native, snapshot(), snapshot(complete=False))["status"], "UNKNOWN")
        broken = snapshot()
        broken["files"][0]["extended"]["ads_status"] = "UNKNOWN"
        self.assertEqual(correlate_extended(native, snapshot(), broken)["status"], "UNKNOWN")

    def test_unchanged_metadata_not_mislabeled(self):
        native = {"status": "COMPLETE", "events": [{"kind": "Zmieniony",
            "path": "sample.txt", "at_utc": "now"}]}
        result = correlate_extended(native, snapshot(), snapshot())
        self.assertNotIn("changes", result["events"][0])
