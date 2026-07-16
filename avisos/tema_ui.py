"""Tema de la interfaz de escritorio.

Este modulo solo afecta a los controles de la aplicacion. El diseño de los
PDF, las plantillas y la identidad visual de los avisos siguen viviendo en
``config.py``, ``estilo.py`` y ``render.py``.
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

NAVY = "#0B3159"
NAVY_HOVER = "#082745"
INK = "#1E293B"
MUTED = "#64748B"
PAGE = "#F7F6F3"
CARD = "#FFFFFF"
SOFT = "#F8FAFC"
BORDER = "#DCE2E8"
SUCCESS = "#2E6B43"
WARNING = "#A16207"

QSS = f"""
QWidget {{ color: {INK}; font-family: "Segoe UI", "Inter", sans-serif; font-size: 13px; }}
QMainWindow, QDialog, QMessageBox, QFileDialog {{ background: {PAGE}; }}
QMenuBar {{ background: {NAVY}; color: white; border: none; padding: 2px 10px; }}
QMenuBar::item {{ padding: 7px 10px; border-radius: 4px; }}
QMenuBar::item:selected {{ background: rgba(255,255,255,0.14); }}
QMenu {{ background: {CARD}; border: 1px solid {BORDER}; padding: 5px; }}
QMenu::item {{ padding: 7px 24px 7px 10px; border-radius: 4px; }}
QMenu::item:selected {{ background: #EDF4FA; color: {NAVY}; }}

QFrame#cabecera {{ background: {NAVY}; border: none; }}
QLabel#marca {{ color: white; font-size: 20px; font-weight: 700; }}
QLabel#marcaSubtitulo {{ color: #C9D8E8; font-size: 11px; }}
QLabel#pasoActivo {{
    background: #E8F0F8; color: {NAVY}; border: 1px solid #BFD0E2;
    border-radius: 14px; padding: 6px 11px; font-weight: 700;
}}
QLabel#pasoInactivo {{ color: #D9E3ED; padding: 6px 8px; }}

QFrame#tarjeta, QWidget#tarjeta {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px;
}}
QLabel#tituloSeccion {{ color: #102A4C; font-size: 17px; font-weight: 700; }}
QLabel#textoSuave {{ color: {MUTED}; font-size: 11px; }}

QGroupBox {{
    background: {CARD}; border: 1px solid {BORDER}; border-radius: 9px;
    margin-top: 12px; padding: 10px 10px 8px; font-weight: 700; color: {NAVY};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 5px; }}
QPushButton, QToolButton {{
    background: {CARD}; color: {INK}; border: 1px solid #C9D2DC;
    border-radius: 7px; padding: 7px 11px; font-weight: 600;
}}
QPushButton:hover, QToolButton:hover {{
    background: #F4F8FB; border-color: #9DB3CF; color: {NAVY};
}}
QPushButton:pressed, QToolButton:pressed {{ background: #E8EFF6; }}
QPushButton:focus, QToolButton:focus {{ border-color: {NAVY}; }}
QPushButton:disabled {{ background: #F3F4F6; color: #A3AAB3; border-color: #E0E3E7; }}
QPushButton#primario {{ background: {NAVY}; color: white; border-color: {NAVY}; }}
QPushButton#primario:hover {{ background: {NAVY_HOVER}; }}
QPushButton#exito {{ background: {SUCCESS}; color: white; border-color: {SUCCESS}; }}

QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QSpinBox, QDateEdit, QListWidget {{
    background: {CARD}; border: 1px solid #C9D2DC; border-radius: 6px;
    padding: 6px 8px; selection-background-color: {NAVY};
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QDateEdit:focus, QListWidget:focus {{ border-color: {NAVY}; }}
QComboBox QAbstractItemView {{
    background: {CARD}; border: 1px solid {BORDER};
    selection-background-color: #E8F0F8; selection-color: {NAVY};
}}
QTextEdit#editorDocumento {{ padding: 22px; }}
QTabWidget::pane {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; }}
QTabBar::tab {{
    background: #EEF3F7; color: {MUTED}; border: 1px solid {BORDER};
    padding: 8px 14px; margin-right: 2px; border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{ background: {CARD}; color: {NAVY}; font-weight: 700; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: {PAGE}; width: 8px; }}
QProgressBar {{
    background: #E6EBF0; border: none; border-radius: 5px;
    min-height: 9px; max-height: 9px; color: transparent;
}}
QProgressBar::chunk {{ background: {NAVY}; border-radius: 5px; }}
QToolTip {{ background: {CARD}; color: {INK}; border: 1px solid {BORDER}; padding: 5px; }}
"""


def aplicar_tema(app) -> None:
    app.setStyle("Fusion")
    paleta = app.palette()
    rol = QPalette.ColorRole
    paleta.setColor(rol.Window, QColor(PAGE))
    paleta.setColor(rol.WindowText, QColor(INK))
    paleta.setColor(rol.Base, QColor(CARD))
    paleta.setColor(rol.AlternateBase, QColor(SOFT))
    paleta.setColor(rol.Text, QColor(INK))
    paleta.setColor(rol.Button, QColor(CARD))
    paleta.setColor(rol.ButtonText, QColor(INK))
    paleta.setColor(rol.Highlight, QColor(NAVY))
    paleta.setColor(rol.HighlightedText, QColor("#FFFFFF"))
    paleta.setColor(rol.PlaceholderText, QColor(MUTED))
    app.setPalette(paleta)
    app.setStyleSheet(QSS)
