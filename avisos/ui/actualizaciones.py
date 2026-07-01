"""Descarga e instalacion de actualizaciones desde GitHub."""
from __future__ import annotations

import os
import tempfile
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QProgressDialog

from .. import updater


class _HiloDescarga(QThread):
    progreso = Signal(int)
    terminado = Signal(str)
    fallo = Signal(str)

    def __init__(self, url: str, destino: Path) -> None:
        super().__init__()
        self._url = url
        self._destino = destino

    def run(self) -> None:
        try:
            peticion = urllib.request.Request(self._url, headers={"User-Agent": "AvisosEMarin"})
            with urllib.request.urlopen(peticion, timeout=20) as resp:
                total = int(resp.headers.get("Content-Length", 0)) or 1
                leido = 0
                with open(self._destino, "wb") as f:
                    while True:
                        bloque = resp.read(65536)
                        if not bloque:
                            break
                        f.write(bloque)
                        leido += len(bloque)
                        self.progreso.emit(int(leido * 100 / total))
            self.terminado.emit(str(self._destino))
        except Exception as e:
            self.fallo.emit(str(e))


def comprobar_actualizaciones(parent, version_actual: str, silencioso: bool) -> None:
    """Comprueba si hay una version mas nueva en GitHub y ofrece instalarla.

    Si `silencioso` es True (comprobacion automatica al abrir), no dice
    nada si ya esta actualizado o si falla la conexion.
    """
    remota = updater.comprobar()
    if remota is None:
        if not silencioso:
            QMessageBox.warning(parent, "Buscar actualizaciones",
                                 "No se ha podido comprobar si hay una versión nueva.\n"
                                 "Revisa tu conexión a internet.")
        return
    if not updater.hay_actualizacion(version_actual, remota):
        if not silencioso:
            QMessageBox.information(parent, "Buscar actualizaciones",
                                     f"Ya tienes la última versión (v{version_actual}).")
        return

    resp = QMessageBox.question(
        parent, "Actualización disponible",
        f"Hay una versión nueva disponible: {remota.tag} (tienes v{version_actual}).\n\n"
        "¿Descargarla e instalarla ahora? La aplicación se cerrará para completar la instalación.",
        QMessageBox.Yes | QMessageBox.No)
    if resp != QMessageBox.Yes:
        return

    destino = Path(tempfile.gettempdir()) / f"AvisosEMarin_Setup_{remota.tag}.exe"
    progreso = QProgressDialog("Descargando actualización…", "Cancelar", 0, 100, parent)
    progreso.setWindowTitle("Actualizando")
    progreso.setMinimumDuration(0)
    progreso.setAutoClose(False)

    hilo = _HiloDescarga(remota.url_instalador, destino)
    hilo.progreso.connect(progreso.setValue)

    def _al_terminar(ruta: str) -> None:
        progreso.close()
        try:
            os.startfile(ruta)  # type: ignore[attr-defined]
        except Exception as e:
            QMessageBox.critical(parent, "Error", f"No se pudo iniciar el instalador:\n{e}")
            return
        QApplication.instance().quit()

    def _al_fallar(mensaje: str) -> None:
        progreso.close()
        QMessageBox.critical(parent, "Error", f"No se pudo descargar la actualización:\n{mensaje}")

    hilo.terminado.connect(_al_terminar)
    hilo.fallo.connect(_al_fallar)
    progreso.canceled.connect(hilo.terminate)
    hilo.start()
    progreso.exec()
