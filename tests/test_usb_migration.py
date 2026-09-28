"""Zestaw USB działa w Center bez odwołania do starego repozytorium."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from prestige_core.usb import plan_prepare, prepare, rollback, update, verify


class UsbMigrationTests(unittest.TestCase):
    def test_prepare_plan_validates_versions_without_writing(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            tool = base / "prestige-fixture"
            tool.mkdir()
            (tool / "metadata.json").write_text(json.dumps({"version": "1.2.3"}))
            target = base / "stick"
            preview = plan_prepare(target, [tool])
            self.assertEqual(preview["versions"], {"prestige-fixture": "1.2.3"})
            self.assertFalse(target.exists())
            with self.assertRaises(ValueError):
                plan_prepare(target, [tool, tool])
            (tool / "metadata.json").write_text(json.dumps({"version": "invalid"}))
            with self.assertRaises(ValueError):
                plan_prepare(target, [tool])
            self.assertFalse(target.exists())

    def test_prepare_multiple_tools(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            tools = []
            for name in ("prestige-one", "prestige-two"):
                tool = base / name
                tool.mkdir()
                (tool / "metadata.json").write_text(json.dumps({"version": "0.1.0"}))
                (tool / "app.py").write_text(name)
                tools.append(tool)
            usb = Path(prepare(base / "stick", tools)["root"])
            self.assertTrue(verify(usb)["ok"])
            self.assertEqual((usb / "Tools/prestige-two/app.py").read_text(), "prestige-two")

    def test_prepare_update_verify_and_rollback(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            tool = base / "prestige-fixture"
            tool.mkdir()
            (tool / "metadata.json").write_text(json.dumps({"version": "0.1.0"}))
            (tool / "app.py").write_text("old")
            usb = Path(prepare(base / "stick", [tool])["root"])
            self.assertTrue(verify(usb)["ok"])
            (tool / "app.py").write_text("new")
            (tool / "metadata.json").write_text(json.dumps({"version": "0.2.0"}))
            self.assertFalse(update(usb, [tool], prepare)["executed"])
            changed = update(usb, [tool], prepare, True)
            self.assertTrue(verify(usb)["ok"])
            self.assertEqual((usb / "Tools/prestige-fixture/app.py").read_text(), "new")
            self.assertTrue(rollback(changed["rollback"], True)["restored"])
            self.assertTrue(verify(usb)["ok"])
            self.assertEqual((usb / "Tools/prestige-fixture/app.py").read_text(), "old")


if __name__ == "__main__":
    unittest.main()
