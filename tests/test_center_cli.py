import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from prestige_cli import main


class CenterCliTests(unittest.TestCase):
    def test_center_dry_run_and_exit_code_forwarding(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--dry-run", "center", "system", "--smoke"]), 0)
        command = json.loads(output.getvalue())["command"]
        self.assertTrue(command[1].endswith("system_center.py"))
        self.assertEqual(command[-1], "--smoke")
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=7)
        self.assertEqual(main(["center", "system", "--smoke"], runner=runner), 7)
        self.assertFalse(calls[0][1]["shell"])

    def test_legacy_default_help_and_return_code(self):
        with patch("prestige_cli.legacy.resolve", return_value=Path("old/app.py")), patch(
                "prestige_cli.legacy.launch", return_value=5) as launch:
            self.assertEqual(main(["legacy", "prestige-file-inspector"]), 5)
            self.assertEqual(launch.call_args.args[-1], ["--help"])

    def test_file_inspection_cli_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.bin"
            source.write_bytes(b"<private-value-123456>")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["file", str(source)]), 0)
            data = json.loads(output.getvalue())
            self.assertEqual(data["tool"], "Prestige File Inspector")
            self.assertEqual(data["data"]["strings"], [])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["file", str(source), "--strings", "--output",
                                       str(Path(directory) / "reports")]), 0)
            paths = [Path(name) for name in json.loads(output.getvalue())["files"]]
            self.assertEqual({path.suffix for path in paths}, {".json", ".txt", ".html"})
            self.assertIn("private-value", json.loads(next(
                path for path in paths if path.suffix == ".json").read_text(encoding="utf-8"))
                ["data"]["strings"][0])
            html_text = next(path for path in paths if path.suffix == ".html").read_text(encoding="utf-8")
            self.assertIn("&lt;private-value", html_text)
            self.assertNotIn("<private-value", html_text)

    def test_file_inspection_pdf_uses_shared_exporter(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.bin"
            source.write_bytes(b"test")
            destination = Path(directory) / "report.pdf"
            output = io.StringIO()
            with patch("prestige_core.pdf_export.export_pdf", return_value=str(destination)) as export_pdf:
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(["file", str(source), "--pdf", str(destination)]), 0)
            self.assertEqual(export_pdf.call_args.args[1], str(destination))
            self.assertEqual(json.loads(output.getvalue())["data"]["name"], source.name)

    def test_ai_local_preview_and_explicit_external_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "report.json"
            source.write_text('{"packet_loss_percent": 5}', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["ai", "local", str(source)]), 0)
            self.assertEqual(json.loads(output.getvalue())["mode"], "LOCAL MODE")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["ai", "preview", str(source)]), 0)
            self.assertFalse(json.loads(output.getvalue())["data_leaves_device"])
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(main(["ai", "external", str(source)]), 1)
            self.assertIn("--send", error.getvalue())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["--dry-run", "ai", "external", str(source), "--send"]), 0)
            self.assertFalse(json.loads(output.getvalue())["data_leaves_device"])
