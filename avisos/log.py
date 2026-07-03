"""Registro de errores y captura de fallos inesperados.

Escribe un archivo de registro en la carpeta de datos del usuario
(%APPDATA%\\AvisosEMarin\\avisos.log) y, si ocurre un error no
controlado, lo registra y muestra un aviso claro en vez de dejar que
la aplicacion se cierre en silencio.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
import traceback

from . import __version__, config

logger = logging.getLogger("avisos")


def ruta_log():
    return config.config_dir() / "avisos.log"


def configurar() -> None:
    """Inicializa el registro a archivo (1 MB, con una copia anterior)."""
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    try:
        handler = logging.handlers.RotatingFileHandler(
            ruta_log(), maxBytes=1_000_000, backupCount=1, encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s", datefmt="%d/%m/%Y %H:%M:%S"))
        logger.addHandler(handler)
    except Exception:
        logger.addHandler(logging.NullHandler())
    logger.info("--- Avisos E. Marin v%s iniciado ---", __version__)


def instalar_excepthook() -> None:
    """Registra los errores no controlados y avisa al usuario sin cerrar
    la aplicacion en silencio."""
    def _hook(tipo, valor, tb) -> None:
        detalle = "".join(traceback.format_exception(tipo, valor, tb))
        logger.error("Error no controlado:\n%s", detalle)
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            if QApplication.instance() is not None:
                QMessageBox.critical(
                    None, "Error inesperado",
                    "Ha ocurrido un error inesperado. La aplicación puede seguir "
                    "funcionando, pero si el problema se repite, reiníciala.\n\n"
                    f"Detalle técnico (guardado en {ruta_log().name}):\n{valor}")
        except Exception:
            pass
        sys.__excepthook__(tipo, valor, tb)

    sys.excepthook = _hook
