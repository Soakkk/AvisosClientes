"""Dialogo de gestion de la base de datos de clientes."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLineEdit, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)

from .. import clients as C


class EditorClienteDialog(QDialog):
    """Formulario para anadir o editar un unico cliente."""

    def __init__(self, parent=None, cliente: C.Cliente | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Editar cliente" if cliente else "Nuevo cliente")
        self.setMinimumWidth(360)

        form = QFormLayout()
        self.txt_nombre = QLineEdit(cliente.nombre if cliente else "")
        self.txt_nif = QLineEdit(cliente.nif if cliente else "")
        self.txt_telefono = QLineEdit(cliente.telefono if cliente else "")
        self.txt_email = QLineEdit(cliente.email if cliente else "")
        form.addRow("Nombre:", self.txt_nombre)
        form.addRow("NIF:", self.txt_nif)
        form.addRow("Teléfono:", self.txt_telefono)
        form.addRow("Email:", self.txt_email)

        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(self._aceptar)
        botones.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(botones)

    def _aceptar(self) -> None:
        if not self.txt_nombre.text().strip():
            QMessageBox.warning(self, "Falta el nombre", "El nombre del cliente es obligatorio.")
            return
        self.accept()

    def cliente(self) -> C.Cliente:
        return C.Cliente(
            nombre=self.txt_nombre.text().strip(),
            nif=self.txt_nif.text().strip(),
            telefono=self.txt_telefono.text().strip(),
            email=self.txt_email.text().strip(),
        )


class ClientesDialog(QDialog):
    """Tabla con alta / edicion / baja de clientes."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clientes")
        self.resize(620, 440)
        self._clientes = C.cargar()

        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["Nombre", "NIF", "Teléfono", "Email"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
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
        cerrar.rejected.connect(self.reject)
        cerrar.accepted.connect(self.accept)
        cerrar.button(QDialogButtonBox.Close).clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabla)
        layout.addLayout(fila_botones)
        layout.addWidget(cerrar)

        self._refrescar_tabla()

    # ------------------------------------------------------------------
    def _refrescar_tabla(self) -> None:
        self._clientes.sort(key=lambda c: c.nombre.lower())
        self.tabla.setRowCount(len(self._clientes))
        for fila, c in enumerate(self._clientes):
            for col, valor in enumerate([c.nombre, c.nif, c.telefono, c.email]):
                self.tabla.setItem(fila, col, QTableWidgetItem(valor))

    def _fila_seleccionada(self) -> int:
        filas = self.tabla.selectionModel().selectedRows()
        return filas[0].row() if filas else -1

    def _anadir(self) -> None:
        dlg = EditorClienteDialog(self)
        if dlg.exec() == QDialog.Accepted:
            nuevo = dlg.cliente()
            if C.buscar(self._clientes, nuevo.nombre):
                QMessageBox.warning(
                    self, "Cliente ya existe",
                    f"Ya hay un cliente llamado «{nuevo.nombre}».")
                return
            self._clientes = C.upsert(self._clientes, nuevo)
            C.guardar(self._clientes)
            self._refrescar_tabla()

    def _editar(self) -> None:
        fila = self._fila_seleccionada()
        if fila < 0:
            return
        original = self._clientes[fila]
        dlg = EditorClienteDialog(self, original)
        if dlg.exec() == QDialog.Accepted:
            self._clientes = C.upsert(self._clientes, dlg.cliente(), original.nombre)
            C.guardar(self._clientes)
            self._refrescar_tabla()

    def _eliminar(self) -> None:
        fila = self._fila_seleccionada()
        if fila < 0:
            return
        nombre = self._clientes[fila].nombre
        resp = QMessageBox.question(
            self, "Eliminar cliente", f"¿Eliminar a «{nombre}»?",
            QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            self._clientes = C.eliminar(self._clientes, nombre)
            C.guardar(self._clientes)
            self._refrescar_tabla()
