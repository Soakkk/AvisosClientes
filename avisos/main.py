"""Punto de entrada de la aplicacion."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import config, log
from .app import MainWindow
from .tema_ui import aplicar_tema


def main() -> int:
    log.configurar()
    log.instalar_excepthook()
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setOrganizationName(config.ORG_NAME)
    aplicar_tema(app)

    # Al salir, esperar a que termine cualquier consulta de actualizaciones
    # en segundo plano (destruir un hilo vivo cerraria la app de golpe).
    from .ui.actualizaciones import esperar_consultas
    app.aboutToQuit.connect(esperar_consultas)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
