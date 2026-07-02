"""Dialogo de gestion de la documentacion opcional reutilizable."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)

from .. import extras as X


class EditorExtraDialog(QDialog):
    """Formulario para anadir o editar una unica entrada de documentacion opcional."""

    def __init__(self, parent=None, extra: X.Extra | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar documentación opcional" if extra else
                            "Nueva documentación opcional")
        self.setMinimumWidth(440)

        form = QFormLayout()
        self.txt_etiqueta = QLineEdit(extra.etiqueta if extra else "")
        self.txt_etiqueta.setPlaceholderText("p. ej. Venta de bienes inmuebles")
        form.addRow("Nombre:", self.txt_etiqueta)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(QLabel("Documentos a solicitar (uno por línea):"))
        self.txt_lineas = QPlainTextEdit("\n".join(extra.lineas) if extra else "")
        self.txt_lineas.setMinimumHeight(130)
        layout.addWidget(self.txt_lineas)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self._aceptar)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _aceptar(self) -> None:
        if not self.txt_etiqueta.text().strip():
            QMessageBox.warning(self, "Falta el nombre",
                                 "Ponle un nombre a esta documentación opcional.")
            return
        if not self.txt_lineas.toPlainText().strip():
            QMessageBox.warning(self, "Sin documentos",
                                 "Añade al menos una línea de documento.")
            return
        self.accept()

    def extra(self) -> X.Extra:
        lineas = [ln.strip() for ln in self.txt_lineas.toPlainText().splitlines() if ln.strip()]
        return X.Extra(etiqueta=self.txt_etiqueta.text().strip(), lineas=lineas)


class ExtrasDialog(QDialog):
    """Tabla con alta / edicion / baja de documentacion opcional."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Documentación opcional")
        self.resize(640, 440)
        self._extras = X.cargar()

        self.tabla = QTableWidget(0, 2)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "Documentos"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.doubleClicked.connect(self._editar)

        btn_anadir = QPushButton("Añadir…")
        btn_anadir.clicked.connect(self._anadir)
        btn_editar = QPushButton("Editar…")
        btn_editar.clicked.connect(self._editar)
        btn_eliminar = QPushButton("Eliminar")
        btn_eliminar.clicked.connect(self._eliminar)
        fila_botones = QHBoxLayout()
        fila_botones.addWidget(btn_anadir)
        fila_botones.addWidget(btn_editar)
        fila_botones.addWidget(btn_eliminar)
        fila_botones.addStretch(1)

        cerrar = QDialogButtonBox(QDialogButtonBox.Close)
        cerrar.button(QDialogButtonBox.Close).clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabla)
        layout.addLayout(fila_botones)
        layout.addWidget(cerrar)

        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        self._extras.sort(key=lambda e: e.etiqueta.lower())
        self.tabla.setRowCount(len(self._extras))
        for fila, e in enumerate(self._extras):
            self.tabla.setItem(fila, 0, QTableWidgetItem(e.etiqueta))
            self.tabla.setItem(fila, 1, QTableWidgetItem(" · ".join(e.lineas)))

    def _fila_seleccionada(self) -> int:
        filas = self.tabla.selectionModel().selectedRows()
        return filas[0].row() if filas else -1

    def _anadir(self) -> None:
        dlg = EditorExtraDialog(self)
        if dlg.exec() == QDialog.Accepted:
            nuevo = dlg.extra()
            if any(e.etiqueta.strip().lower() == nuevo.etiqueta.strip().lower()
                   for e in self._extras):
                QMessageBox.warning(self, "Ya existe",
                                     f"Ya hay una entrada llamada «{nuevo.etiqueta}».")
                return
            self._extras = X.upsert(self._extras, nuevo)
            X.guardar(self._extras)
            self._refrescar_tabla()

    def _editar(self) -> None:
        fila = self._fila_seleccionada()
        if fila < 0:
            return
        original = self._extras[fila]
        dlg = EditorExtraDialog(self, original)
        if dlg.exec() == QDialog.Accepted:
            self._extras = X.upsert(self._extras, dlg.extra(), original.etiqueta)
            X.guardar(self._extras)
            self._refrescar_tabla()

    def _eliminar(self) -> None:
        fila = self._fila_seleccionada()
        if fila < 0:
            return
        etiqueta = self._extras[fila].etiqueta
        resp = QMessageBox.question(
            self, "Eliminar", f"¿Eliminar «{etiqueta}»?",
            QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            self._extras = X.eliminar(self._extras, etiqueta)
            X.guardar(self._extras)
            self._refrescar_tabla()
