"""Dialogo de consulta del historial de avisos generados."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from .. import history as H


class HistorialDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Historial de avisos generados")
        self.resize(760, 460)
        self._entradas = list(reversed(H.cargar()))

        fila_busqueda = QHBoxLayout()
        fila_busqueda.addWidget(QLabel("Buscar cliente:"))
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Escribe un nombre para filtrar…")
        self.txt_buscar.textChanged.connect(self._refrescar_tabla)
        fila_busqueda.addWidget(self.txt_buscar, 1)

        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(
            ["Fecha", "Plantilla", "Periodo", "Cliente", "Archivo"])
        self.tabla.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.doubleClicked.connect(self._abrir_pdf)

        fila_botones = QHBoxLayout()
        btn_abrir = QPushButton("Abrir PDF")
        btn_abrir.clicked.connect(self._abrir_pdf)
        btn_carpeta = QPushButton("Abrir carpeta")
        btn_carpeta.clicked.connect(self._abrir_carpeta)
        fila_botones.addWidget(btn_abrir)
        fila_botones.addWidget(btn_carpeta)
        fila_botones.addStretch(1)

        cerrar = QDialogButtonBox(QDialogButtonBox.Close)
        cerrar.button(QDialogButtonBox.Close).clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addLayout(fila_busqueda)
        layout.addWidget(self.tabla)
        layout.addLayout(fila_botones)
        layout.addWidget(cerrar)

        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        filtro = self.txt_buscar.text().strip().lower()
        visibles = [e for e in self._entradas if filtro in e.cliente.lower()] if filtro else self._entradas
        self._visibles = visibles
        self.tabla.setRowCount(len(visibles))
        for fila, e in enumerate(visibles):
            valores = [e.fecha_hora, e.plantilla, e.periodo + " " + str(e.anio), e.cliente, e.ruta]
            for col, valor in enumerate(valores):
                self.tabla.setItem(fila, col, QTableWidgetItem(valor))

    def _fila_seleccionada(self) -> int:
        filas = self.tabla.selectionModel().selectedRows()
        return filas[0].row() if filas else -1

    def _ruta_seleccionada(self) -> Path | None:
        fila = self._fila_seleccionada()
        if fila < 0:
            return None
        return Path(self._visibles[fila].ruta)

    def _abrir_pdf(self) -> None:
        ruta = self._ruta_seleccionada()
        if ruta is None:
            return
        if not ruta.exists():
            QMessageBox.warning(self, "Archivo no encontrado",
                                 f"El archivo ya no está en esta ubicación:\n{ruta}")
            return
        os.startfile(str(ruta))  # type: ignore[attr-defined]

    def _abrir_carpeta(self) -> None:
        ruta = self._ruta_seleccionada()
        if ruta is None:
            return
        carpeta = ruta.parent
        if not carpeta.exists():
            QMessageBox.warning(self, "Carpeta no encontrada",
                                 f"La carpeta ya no existe:\n{carpeta}")
            return
        if ruta.exists():
            subprocess.run(["explorer", "/select," + str(ruta)])
        else:
            os.startfile(str(carpeta))  # type: ignore[attr-defined]
