"""Generar el mismo aviso (misma plantilla y mismos datos) para varios
clientes de golpe: una copia individual del PDF por cada nombre elegido.
"""
from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from .. import clients as C
from .. import history as H
from ..render import render_pdf
from ..templates import Contexto, Plantilla
from ..util import nombre_archivo


class LoteDialog(QDialog):
    def __init__(self, parent, ctx_base: Contexto, plantilla: Plantilla,
                 carpeta_inicial: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generar para varios clientes")
        self.resize(520, 560)
        self._ctx_base = ctx_base
        self._plantilla = plantilla
        self._carpeta = carpeta_inicial

        info = QLabel(
            f"Se generará un PDF individual por cada cliente marcado, usando:\n"
            f"«{plantilla.nombre}» — {ctx_base.periodo_largo} de {ctx_base.anio}")
        info.setWordWrap(True)

        self.lista = QListWidget()
        for c in sorted(C.cargar(), key=lambda x: x.nombre.lower()):
            item = QListWidgetItem(c.nombre)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.lista.addItem(item)

        fila_marcar = QHBoxLayout()
        btn_todos = QPushButton("Marcar todos")
        btn_todos.clicked.connect(lambda: self._marcar_todos(Qt.Checked))
        btn_ninguno = QPushButton("Desmarcar todos")
        btn_ninguno.clicked.connect(lambda: self._marcar_todos(Qt.Unchecked))
        fila_marcar.addWidget(btn_todos)
        fila_marcar.addWidget(btn_ninguno)
        fila_marcar.addStretch(1)

        self.txt_sueltos = QPlainTextEdit()
        self.txt_sueltos.setPlaceholderText(
            "Nombres sueltos que no estén en la base de datos (uno por línea, opcional)")
        self.txt_sueltos.setMaximumHeight(80)

        fila_carpeta = QHBoxLayout()
        self.lbl_carpeta = QLabel(self._carpeta)
        self.lbl_carpeta.setWordWrap(True)
        btn_carpeta = QPushButton("Elegir carpeta…")
        btn_carpeta.clicked.connect(self._elegir_carpeta)
        fila_carpeta.addWidget(QLabel("Guardar en:"))
        fila_carpeta.addWidget(self.lbl_carpeta, 1)
        fila_carpeta.addWidget(btn_carpeta)

        fila_botones = QHBoxLayout()
        btn_generar = QPushButton("Generar avisos")
        btn_generar.setMinimumHeight(36)
        btn_generar.clicked.connect(self._generar)
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        fila_botones.addWidget(btn_generar)
        fila_botones.addWidget(btn_cancelar)

        layout = QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(QLabel("Clientes de la base de datos:"))
        layout.addWidget(self.lista, 1)
        layout.addLayout(fila_marcar)
        layout.addWidget(self.txt_sueltos)
        layout.addLayout(fila_carpeta)
        layout.addLayout(fila_botones)

    # ------------------------------------------------------------------
    def _marcar_todos(self, estado) -> None:
        for i in range(self.lista.count()):
            self.lista.item(i).setCheckState(estado)

    def _elegir_carpeta(self) -> None:
        carpeta = QFileDialog.getExistingDirectory(self, "Elegir carpeta destino", self._carpeta)
        if carpeta:
            self._carpeta = carpeta
            self.lbl_carpeta.setText(carpeta)

    def _nombres_elegidos(self) -> list[str]:
        nombres = [self.lista.item(i).text() for i in range(self.lista.count())
                   if self.lista.item(i).checkState() == Qt.Checked]
        sueltos = [ln.strip() for ln in self.txt_sueltos.toPlainText().splitlines() if ln.strip()]
        return nombres + sueltos

    def _generar(self) -> None:
        nombres = self._nombres_elegidos()
        if not nombres:
            QMessageBox.warning(self, "Sin clientes",
                                 "Marca al menos un cliente o escribe algún nombre suelto.")
            return
        carpeta = Path(self._carpeta)
        if not carpeta.exists():
            QMessageBox.warning(self, "Carpeta no válida", "Elige una carpeta de destino válida.")
            return

        generados = 0
        errores: list[str] = []
        for nombre in nombres:
            ctx = replace(self._ctx_base, cliente=nombre)
            ruta = carpeta / nombre_archivo(self._plantilla, ctx)
            try:
                render_pdf(ctx, self._plantilla, ruta)
                H.registrar(self._plantilla.nombre, ctx.periodo_corto, ctx.anio, nombre, str(ruta))
                generados += 1
            except Exception as e:
                errores.append(f"{nombre}: {e}")

        mensaje = f"Se han generado {generados} de {len(nombres)} avisos en:\n{carpeta}"
        if errores:
            mensaje += "\n\nErrores:\n" + "\n".join(errores)
        QMessageBox.information(self, "Generación en lote", mensaje)
        resp = QMessageBox.question(
            self, "Abrir carpeta", "¿Abrir la carpeta de destino?",
            QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            os.startfile(str(carpeta))  # type: ignore[attr-defined]
        self.accept()
