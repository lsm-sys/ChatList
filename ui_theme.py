"""Тема интерфейса и размер шрифта."""

from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

from db import Database

THEME_LIGHT = "light"
THEME_DARK = "dark"

DEFAULT_FONT_SIZE = 10

DARK_STYLESHEET = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
}
QMainWindow, QDialog {
    background-color: #1e1e1e;
}
QMenuBar {
    background-color: #2b2b2b;
    color: #e0e0e0;
}
QMenuBar::item:selected {
    background-color: #3d3d3d;
}
QMenu {
    background-color: #2b2b2b;
    color: #e0e0e0;
    border: 1px solid #444;
}
QMenu::item:selected {
    background-color: #3d5afe;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
    background-color: #2b2b2b;
    color: #e0e0e0;
    border: 1px solid #555;
    selection-background-color: #3d5afe;
}
QComboBox QAbstractItemView {
    background-color: #2b2b2b;
    color: #e0e0e0;
    selection-background-color: #3d5afe;
}
QPushButton {
    background-color: #333;
    color: #e0e0e0;
    border: 1px solid #555;
    padding: 4px 10px;
}
QPushButton:hover {
    background-color: #444;
}
QPushButton:disabled {
    color: #888;
    background-color: #2a2a2a;
}
QTableWidget, QTableView {
    background-color: #252525;
    alternate-background-color: #2a2a2a;
    color: #e0e0e0;
    gridline-color: #444;
    selection-background-color: #3d5afe;
}
QHeaderView::section {
    background-color: #333;
    color: #e0e0e0;
    border: 1px solid #444;
    padding: 4px;
}
QListWidget {
    background-color: #252525;
    color: #e0e0e0;
    border: 1px solid #555;
}
QGroupBox {
    border: 1px solid #555;
    margin-top: 8px;
    color: #e0e0e0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}
QCheckBox, QLabel {
    color: #e0e0e0;
}
QStatusBar {
    background-color: #2b2b2b;
    color: #ccc;
}
QScrollBar:vertical {
    background: #2b2b2b;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #555;
    min-height: 20px;
    border-radius: 4px;
}
QProgressDialog {
    background-color: #1e1e1e;
}
"""


def get_theme(db: Database) -> str:
    theme = db.get_setting("ui_theme", THEME_LIGHT) or THEME_LIGHT
    return theme if theme in (THEME_LIGHT, THEME_DARK) else THEME_LIGHT


def get_font_size(db: Database) -> int:
    raw = db.get_setting("font_size", str(DEFAULT_FONT_SIZE)) or str(DEFAULT_FONT_SIZE)
    try:
        size = int(raw)
    except ValueError:
        size = DEFAULT_FONT_SIZE
    return max(8, min(24, size))


def apply_ui_settings(app: QApplication, db: Database) -> None:
    theme = get_theme(db)
    font_size = get_font_size(db)

    app.setStyleSheet(DARK_STYLESHEET if theme == THEME_DARK else "")

    font = QFont(app.font())
    font.setPointSize(font_size)
    app.setFont(font)
