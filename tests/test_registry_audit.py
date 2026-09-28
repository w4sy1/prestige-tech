from threading import Event
import unittest

from prestige_core.registry_audit import audit_catalog
from prestige_core.registry_read import OPERATIONS
from tests.test_registry_read import FakeRegistry


class RegistryAuditTests(unittest.TestCase):
    def test_summary_does_not_store_values(self):
        catalog = (OPERATIONS[5], OPERATIONS[6])
        fake = FakeRegistry({"HideFileExt": (0, 4), "Hidden": (1, 4)})
        progress = []
        result = audit_catalog(catalog, registry=fake, platform="nt",
                               on_progress=lambda done, total: progress.append((done, total)))
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(result["counts"], {"OK": 2})
        self.assertEqual(progress[-1], (2, 2))
        self.assertNotIn("HideFileExt", str(result))

    def test_cancel_and_duplicate_catalog(self):
        flag = Event()
        flag.set()
        result = audit_catalog((OPERATIONS[0],), cancel_event=flag)
        self.assertEqual(result["status"], "CANCELLED")
        self.assertEqual(result["processed"], 0)
        with self.assertRaises(ValueError):
            audit_catalog((OPERATIONS[0], OPERATIONS[0]))


if __name__ == "__main__":
    unittest.main()
