"""Punto de entrada de la aplicacion."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import config
from .app import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.ORG_NAME)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
