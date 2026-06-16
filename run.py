"""
QuestCut-AI - Launcher
=========================================
Run from Windows desktop to launch the application.
"""
import sys
import os

# Ensure the source package is on the path
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
if SOURCE_DIR not in sys.path:
    sys.path.insert(0, SOURCE_DIR)

from PySide6.QtWidgets import QApplication
from src.ui.elite_main_window import EliteMainWindow


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle('Fusion')

    # Dark theme palette
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 15, 16))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(26, 26, 29))
    palette.setColor(QPalette.AlternateBase, QColor(42, 42, 47))
    palette.setColor(QPalette.ToolTipBase, QColor(42, 42, 47))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(42, 42, 47))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(79, 70, 229))
    palette.setColor(QPalette.Highlight, QColor(79, 70, 229))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = EliteMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
