import os
import unittest
import unittest.mock

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import numpy as np
from PIL import Image
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from src.ui.elite_main_window import EliteMainWindow


class EditorSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QSettings('QuestCut', 'QuestCut-AI').setValue('has_shown_welcome', True)
        cls.app = QApplication.instance() or QApplication([])

    def test_smart_crop_transform_and_recomposite_keep_original_canvas_size(self):
        window = EliteMainWindow()
        try:
            original = Image.new('RGBA', (20, 20), (0, 0, 255, 255))
            mask = np.zeros((20, 20), dtype=np.uint8)
            mask[8:12, 7:13] = 255
            window._original_image = original
            window._current_mask = mask

            transform = window._calculate_smart_crop_transform()
            self.assertIsNotNone(transform)
            scale, offset_x, offset_y = transform
            self.assertGreater(scale, 1.0)

            result = window._compose_with_current_settings(original, mask)
            self.assertEqual(result.size, original.size)
            self.assertEqual(result.mode, 'RGBA')
        finally:
            window.close()

    def test_undo_redo_restores_position_controls_after_history_refactor(self):
        window = EliteMainWindow()
        try:
            original = Image.new('RGBA', (20, 20), (255, 0, 0, 255))
            mask = np.zeros((20, 20), dtype=np.uint8)
            mask[5:15, 5:15] = 255
            window._original_image = original
            window._current_mask = mask
            window._processed_image = original.copy()
            window.editor_screen.canvas.set_image(original)
            window.editor_screen.canvas.set_result(original.copy(), animate=False)

            window.editor_screen.control_panel.set_position_values(1, 0, 0, 0, False, False)
            window._mark_history_baseline()
            self.assertFalse(window._history.can_undo)

            window._push_history()
            window.editor_screen.control_panel.set_position_values(1.5, 12, -8, 0, False, False)
            window._recomposite_with_mask()
            self.assertTrue(window._history.can_undo)
            self.assertEqual(window.editor_screen.control_panel.get_position_settings()['x'], 12)

            window._undo()
            restored = window.editor_screen.control_panel.get_position_settings()
            self.assertAlmostEqual(restored['scale'], 1.0)
            self.assertEqual(restored['x'], 0)
            self.assertEqual(restored['y'], 0)
            self.assertTrue(window._history.can_redo)

            window._redo()
            redone = window.editor_screen.control_panel.get_position_settings()
            self.assertAlmostEqual(redone['scale'], 1.5)
            self.assertEqual(redone['x'], 12)
            self.assertEqual(redone['y'], -8)
        finally:
            window.close()

    def test_question_mark_shortcut_opens_shortcuts_dialog(self):
        window = EliteMainWindow()
        try:
            with unittest.mock.patch('src.ui.elite_main_window.ShortcutsDialog.show_shortcuts') as show_shortcuts:
                window._show_shortcuts()
                show_shortcuts.assert_called_once_with(window)
        finally:
            window.close()


if __name__ == '__main__':
    unittest.main()
