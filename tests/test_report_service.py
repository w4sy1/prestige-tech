import importlib.util
import tempfile
import unittest
from pathlib import Path

from prestige_core.report_service import LABELS, render, template, validate
from prestige_core.pdf_export import export_pdf


def sample():
    return {**template(), "numer_zlecenia": "PT-001", "klient": "Klient próbny",
            "urzadzenie": "Laptop", "zgloszony_problem": "Nie uruchamia się",
            "diagnoza": "Błąd testowy <script>alert(1)</script>",
            "wykonane_czynnosci": "Kontrola odczytowa", "test_koncowy": "PASS"}


class ReportServiceTests(unittest.TestCase):
    def test_template_validation_and_html_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            output = render(sample(), directory)
            self.assertEqual(len(output["files"]), 3)
            html_path = next(Path(path) for path in output["files"] if path.endswith(".html"))
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("&lt;script&gt;", html)
            self.assertNotIn("<script>", html)
            self.assertTrue(all(Path(path).is_file() for path in output["files"]))
            with self.assertRaises(ValueError):
                validate({**sample(), "czas_pracy_min": -1})

    @unittest.skipUnless(importlib.util.find_spec("reportlab"), "reportlab unavailable")
    def test_pdf_unicode_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "repair.pdf"
            record = sample()
            export_pdf({LABELS[key]: value for key, value in record.items()}, target, "Raport serwisowy")
            self.assertTrue(target.read_bytes().startswith(b"%PDF-"))
            self.assertGreater(target.stat().st_size, 3000)
            with self.assertRaises(FileExistsError):
                export_pdf(record, target)
