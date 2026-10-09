import os
import unittest
from unittest.mock import patch

from prestige_core.registry_guides import GUIDES, completion_instructions
from prestige_core.registry_transactions import OPERATIONS
from prestige_core.registry_policy_changes import OPERATIONS as POLICY_OPERATIONS


class RegistryGuideTests(unittest.TestCase):
    def test_completion_instructions_explain_apply_and_undo(self):
        applied = completion_instructions("REG-WRITE-001", "C:/copy.json")
        self.assertIn("Co zrobiono:", applied)
        self.assertIn("Jak sprawdzić:", applied)
        self.assertIn("Jak cofnąć:", applied)
        self.assertIn("C:/copy.json", applied)
        self.assertIn("Restart:", applied)
        self.assertIn("Uruchom ponownie Windows", completion_instructions(
            "REG-WRITE-013", "C:/policy.json"))
        undone = completion_instructions("REG-WRITE-001", "C:/copy.json", undone=True)
        self.assertIn("Przywrócono", undone)

    def test_every_existing_change_has_plain_language_guide(self):
        self.assertEqual(set(GUIDES), {"REG-WRITE-001"} | {item.id for item in OPERATIONS}
                         | {item.id for item in POLICY_OPERATIONS})
        for guide in GUIDES.values():
            self.assertTrue(guide.summary and guide.impact and guide.after)
            self.assertIn(guide.edition, ("FREE", "PRO"))

    def test_free_window_refuses_pro_write_before_registry_access(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from prestige_registry.gui import RegistryWindow
        app = QApplication.instance() or QApplication([])
        window = RegistryWindow()
        self.assertFalse(window.experimental_policies.isChecked())
        window.change_choice.setCurrentIndex(2)
        self.assertFalse(window.change_apply_button.isEnabled())
        with patch("prestige_registry.gui.plan_change") as plan:
            window.apply_selected_change()
            plan.assert_not_called()
        self.assertIn("PRO", window.status.text())
        with patch("prestige_registry.gui.plan_policy_change") as policy_plan:
            window.apply_selected_policy()
            policy_plan.assert_not_called()
        self.assertIn("PRO", window.status.text())
        window.close()
