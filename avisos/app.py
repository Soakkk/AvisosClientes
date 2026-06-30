"""Ventana principal del generador de avisos."""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from . import config
from . import templates as T
from .render import render_pdf, render_preview


def _slug(texto: str) -> str:
    texto = texto.lower()
    repl = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
            "º": "", "ª": "", "·": "", ".": "", ",": ""}
    for k, v in repl.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto or "aviso"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.resize(1180, 800)
        icon = config.asset("EM_logo_horizontal_claro.jpg")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        self._docs_tocados = False  # si el usuario edito la lista manualmente
        self._construir_ui()
        self._cargar_ajustes()
        self._on_plantilla_cambia(forzar_docs=not self._docs_tocados)
        self._programar_preview()

    # ------------------------------------------------------------------ UI
    def _construir_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QHBoxLayout(central)
        raiz.setContentsMargins(14, 14, 14, 14)
        raiz.setSpacing(14)

        # ---- Panel izquierdo: formulario ----
        panel = QWidget()
        panel.setMaximumWidth(440)
        form_scroll = QScrollArea()
        form_scroll.setWidgetResizable(True)
        form_scroll.setWidget(panel)
        form_scroll.setFrameShape(QFrame.NoFrame)
        col = QVBoxLayout(panel)
        col.setSpacing(12)

        titulo = QLabel("Generador de avisos")
        f = QFont()
        f.setPointSize(15)
        f.setBold(True)
        titulo.setFont(f)
        col.addWidget(titulo)

        # Plantilla
        gb_pl = QGroupBox("Plantilla")
        ly_pl = QVBoxLayout(gb_pl)
        self.cmb_plantilla = QComboBox()
        for p in T.PLANTILLAS:
            self.cmb_plantilla.addItem(f"{p.grupo} · {p.nombre}", p.id)
        self.cmb_plantilla.currentIndexChanged.connect(
            lambda: self._on_plantilla_cambia(forzar_docs=not self._docs_tocados))
        ly_pl.addWidget(self.cmb_plantilla)
        col.addWidget(gb_pl)

        # Datos
        gb_d = QGroupBox("Datos del aviso")
        ly_d = QFormLayout(gb_d)
        ly_d.setLabelAlignment(Qt.AlignRight)

        self.cmb_periodo = QComboBox()
        for clave, info in T.PERIODOS.items():
            self.cmb_periodo.addItem(info["largo"], clave)
        self.cmb_periodo.currentIndexChanged.connect(self._on_periodo_cambia)
        ly_d.addRow("Periodo:", self.cmb_periodo)

        self.spin_anio = QSpinBox()
        self.spin_anio.setRange(2000, 2100)
        self.spin_anio.setValue(date.today().year)
        self.spin_anio.valueChanged.connect(self._on_periodo_cambia)
        ly_d.addRow("Año:", self.spin_anio)

        self.txt_cliente = QLineEdit()
        self.txt_cliente.setPlaceholderText("(vacío = «Estimado/a cliente»)")
        self.txt_cliente.textChanged.connect(self._programar_preview)
        ly_d.addRow("Cliente:", self.txt_cliente)

        self.date_limite = QDateEdit()
        self.date_limite.setCalendarPopup(True)
        self.date_limite.setDisplayFormat("dd/MM/yyyy")
        self.date_limite.dateChanged.connect(self._programar_preview)
        ly_d.addRow("Fecha límite:", self.date_limite)

        self.chk_navidad = QCheckBox("Incluir felicitación navideña")
        self.chk_navidad.stateChanged.connect(self._programar_preview)
        ly_d.addRow("", self.chk_navidad)

        col.addWidget(gb_d)

        # Documentos
        gb_doc = QGroupBox("Documentos solicitados (uno por línea)")
        ly_doc = QVBoxLayout(gb_doc)
        self.txt_docs = QPlainTextEdit()
        self.txt_docs.setMinimumHeight(120)
        self.txt_docs.textChanged.connect(self._on_docs_editados)
        ly_doc.addWidget(self.txt_docs)
        btn_reset = QPushButton("Restablecer lista de la plantilla")
        btn_reset.clicked.connect(self._reset_docs)
        ly_doc.addWidget(btn_reset)
        col.addWidget(gb_doc)

        # Notas
        gb_n = QGroupBox("Notas adicionales (opcional)")
        ly_n = QVBoxLayout(gb_n)
        self.txt_notas = QPlainTextEdit()
        self.txt_notas.setMaximumHeight(80)
        self.txt_notas.textChanged.connect(self._programar_preview)
        ly_n.addWidget(self.txt_notas)
        col.addWidget(gb_n)

        # Botones
        fila = QHBoxLayout()
        self.btn_pdf = QPushButton("Generar y guardar PDF…")
        self.btn_pdf.setMinimumHeight(40)
        self.btn_pdf.clicked.connect(self._guardar_pdf)
        fila.addWidget(self.btn_pdf)
        col.addLayout(fila)
        col.addStretch(1)

        raiz.addWidget(form_scroll)

        # ---- Panel derecho: vista previa ----
        der = QVBoxLayout()
        lbl = QLabel("Vista previa")
        lbl.setFont(f)
        der.addWidget(lbl)
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background:#9a9a9a;")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview)
        der.addWidget(scroll, 1)
        raiz.addLayout(der, 1)

        self._preview_img = None
        # Repinta el preview al redimensionar
        self.preview.resizeEvent = self._on_preview_resize  # type: ignore

        # Timer para no regenerar en cada tecla
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._actualizar_preview)

    # --------------------------------------------------------------- estado
    def _plantilla_actual(self) -> T.Plantilla:
        return T.por_id(self.cmb_plantilla.currentData())

    def _contexto(self) -> T.Contexto:
        qd = self.date_limite.date()
        return T.Contexto(
            periodo=self.cmb_periodo.currentData(),
            anio=self.spin_anio.value(),
            cliente=self.txt_cliente.text(),
            fecha_limite=date(qd.year(), qd.month(), qd.day()),
            documentos=[ln for ln in self.txt_docs.toPlainText().splitlines()],
            navidad=self.chk_navidad.isChecked(),
            notas=self.txt_notas.toPlainText(),
        )

    def _on_plantilla_cambia(self, forzar_docs: bool = True) -> None:
        p = self._plantilla_actual()
        self.chk_navidad.setVisible(p.usa_navidad)
        if p.id == "cierre_anual":
            self._set_periodo("4T")
        if forzar_docs:
            self._set_docs(p.documentos_def)
        self._on_periodo_cambia()

    def _on_periodo_cambia(self) -> None:
        clave = self.cmb_periodo.currentData()
        d = T.plazo_por_defecto(clave, self.spin_anio.value())
        self.date_limite.blockSignals(True)
        self.date_limite.setDate(QDate(d.year, d.month, d.day))
        self.date_limite.blockSignals(False)
        self._programar_preview()

    def _on_docs_editados(self) -> None:
        self._docs_tocados = True
        self._programar_preview()

    def _set_docs(self, docs: list[str]) -> None:
        self.txt_docs.blockSignals(True)
        self.txt_docs.setPlainText("\n".join(docs))
        self.txt_docs.blockSignals(False)
        self._docs_tocados = False

    def _reset_docs(self) -> None:
        self._set_docs(self._plantilla_actual().documentos_def)
        self._programar_preview()

    def _set_periodo(self, clave: str) -> None:
        idx = self.cmb_periodo.findData(clave)
        if idx >= 0:
            self.cmb_periodo.blockSignals(True)
            self.cmb_periodo.setCurrentIndex(idx)
            self.cmb_periodo.blockSignals(False)

    # -------------------------------------------------------------- preview
    def _programar_preview(self) -> None:
        self._timer.start()

    def _actualizar_preview(self) -> None:
        try:
            img = render_preview(self._contexto(), self._plantilla_actual())
            self._preview_img = QPixmap.fromImage(img)
            self._pintar_preview()
        except Exception as e:  # no romper la UI por un fallo de render
            self.preview.setText(f"Error al generar la vista previa:\n{e}")

    def _pintar_preview(self) -> None:
        if not self._preview_img:
            return
        area = self.preview.size()
        escalado = self._preview_img.scaled(
            area, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(escalado)

    def _on_preview_resize(self, event) -> None:
        self._pintar_preview()
        QLabel.resizeEvent(self.preview, event)

    # ----------------------------------------------------------------- PDF
    def _nombre_sugerido(self) -> str:
        ctx = self._contexto()
        partes = [_slug(self._plantilla_actual().nombre),
                  ctx.periodo_corto, str(ctx.anio)]
        if ctx.cliente.strip():
            partes.append(_slug(ctx.cliente))
        return "AVISO_" + "_".join(partes).upper() + ".pdf"

    def _guardar_pdf(self) -> None:
        carpeta = self._ultima_carpeta()
        destino, _ = QFileDialog.getSaveFileName(
            self, "Guardar aviso en PDF",
            str(Path(carpeta) / self._nombre_sugerido()),
            "PDF (*.pdf)")
        if not destino:
            return
        try:
            render_pdf(self._contexto(), self._plantilla_actual(), destino)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{e}")
            return
        self._guardar_ajustes(Path(destino).parent)
        resp = QMessageBox.question(
            self, "PDF generado",
            f"Aviso guardado en:\n{destino}\n\n¿Abrir el archivo?",
            QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            import os
            try:
                os.startfile(destino)  # type: ignore[attr-defined]
            except Exception:
                pass

    # ------------------------------------------------------------- ajustes
    def _ultima_carpeta(self) -> str:
        try:
            data = json.loads(config.settings_path().read_text("utf-8"))
            return data.get("ultima_carpeta") or str(Path.home() / "Desktop")
        except Exception:
            return str(Path.home() / "Desktop")

    def _cargar_ajustes(self) -> None:
        try:
            data = json.loads(config.settings_path().read_text("utf-8"))
        except Exception:
            return
        pid = data.get("plantilla")
        if pid:
            idx = self.cmb_plantilla.findData(pid)
            if idx >= 0:
                self.cmb_plantilla.setCurrentIndex(idx)

    def _guardar_ajustes(self, carpeta: Path) -> None:
        data = {
            "plantilla": self.cmb_plantilla.currentData(),
            "ultima_carpeta": str(carpeta),
        }
        try:
            config.settings_path().write_text(
                json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        except Exception:
            pass
