import os
import unittest

from prestige_core.link_check import inspect_link


class LinkCheckTests(unittest.TestCase):
    def test_at_sign_exposes_actual_domain_without_opening_url(self):
        result = inspect_link("https://bank.example@other.example/login?token=private")
        self.assertEqual(result["domain"], "other.example")
        self.assertEqual(result["status"], "REVIEW")
        self.assertFalse(result["opened_page"])
        self.assertFalse(result["sent_to_network"])
        self.assertNotIn("private", str(result))

    def test_plain_url_never_claims_safe(self):
        result = inspect_link("https://example.com")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertIn("nie potwierdza", result["message"])

    def test_invalid_scheme_is_rejected(self):
        for url in ("javascript:alert(1)", "file:///C:/test", "https://bad.example\\@good.example"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                inspect_link(url)

    def test_security_gui_displays_only_local_domain_and_findings(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_security.gui import SecurityCenterWindow
        app = QApplication.instance() or QApplication([])
        window = SecurityCenterWindow()
        try:
            window.link_input.setText("https://trusted.example@other.example/path?secret=private")
            window.check_link()
            self.assertIn("other.example", window.result.toPlainText())
            self.assertNotIn("private", window.result.toPlainText())
            self.assertIn("niczego nie wysłano", window.result.toPlainText())
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
