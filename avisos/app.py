"""Ventana principal del generador de avisos."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QStringListModel, Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QDateEdit, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPlainTextEdit, QPushButton, QScrollArea, QSpinBox, QSplitter,
    QVBoxLayout, QWidget,
)

from . import __version__
from . import clients as C
from . import config
from . import history as H
from . import templates as T
from .render import render_pdf, render_preview
from .ui.actualizaciones import comprobar_actualizaciones
from .ui.clientes import ClientesDialog
from .ui.formato import FormatoDialog
from .ui.historial import HistorialDialog
from .ui.lote import LoteDialog
from .ui.plantillas import PlantillaEditorDialog
from .ui.preview_widget import PreviewPanel
from .util import nombre_archivo, ruta_sin_colision


def _ajustar_desplegable(combo: QComboBox) -> None:
    """Evita que el desplegable corte el texto largo: ensancha el popup
    (no el propio combo cerrado) y anade tooltip con el texto completo."""
    fm = combo.fontMetrics()
    ancho = max((fm.horizontalAdvance(combo.itemText(i)) for i in range(combo.count())), default=0)
    combo.view().setMinimumWidth(ancho + 40)
    for i in range(combo.count()):
        combo.setItemData(i, combo.itemText(i), Qt.ToolTipRole)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{config.APP_NAME} — v{__version__}")
        self.resize(1360, 880)
        icon = config.asset("EM_logo_horizontal_claro.jpg")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        self._docs_tocados = False  # si el usuario edito la lista manualmente
        self._editor_plantillas: PlantillaEditorDialog | None = None
        self._editor_formato: FormatoDialog | None = None
        self._comprobacion_inicial_hecha = False
        self._construir_menu()
        self._construir_ui()
        self._aplicar_periodo_sugerido()
        self._cargar_ajustes()
        self._refrescar_completer_clientes()
        self._on_plantilla_cambia(forzar_docs=not self._docs_tocados)
        self._programar_preview()

    # ------------------------------------------------------------------ UI
    def _construir_menu(self) -> None:
        menu = self.menuBar().addMenu("Herramientas")
        menu.addAction("Clientes…", self._abrir_clientes)
        menu.addAction("Generar para varios clientes…", self._abrir_lote)
        menu.addAction("Historial de avisos…", self._abrir_historial)
        menu.addSeparator()
        menu.addAction("Editar plantillas…", self._abrir_editor_plantillas)
        menu.addAction("Formato del documento…", self._abrir_formato)

        ayuda = self.menuBar().addMenu("Ayuda")
        ayuda.addAction("Buscar actualizaciones…", self._buscar_actualizaciones_manual)

    def _construir_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(14, 14, 14, 14)

        splitter = QSplitter(Qt.Horizontal)
        raiz.addWidget(splitter)

        # ---- Panel izquierdo: formulario ----
        panel = QWidget()
        panel.setMinimumWidth(320)
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
        _ajustar_desplegable(self.cmb_plantilla)
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
        _ajustar_desplegable(self.cmb_periodo)
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
        self.date_limite.dateChanged.connect(self._on_fecha_cambia)
        ly_d.addRow("Fecha límite:", self.date_limite)

        self.lbl_aviso_fecha = QLabel("")
        self.lbl_aviso_fecha.setStyleSheet("color:#B3541E; font-size:11px;")
        self.lbl_aviso_fecha.setWordWrap(True)
        ly_d.addRow("", self.lbl_aviso_fecha)

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
        self.btn_pdf = QPushButton("Generar y guardar PDF en el Escritorio")
        self.btn_pdf.setMinimumHeight(40)
        self.btn_pdf.clicked.connect(self._guardar_pdf)
        fila.addWidget(self.btn_pdf)
        col.addLayout(fila)
        col.addStretch(1)

        splitter.addWidget(form_scroll)

        # ---- Panel derecho: vista previa ----
        der_widget = QWidget()
        der = QVBoxLayout(der_widget)
        der.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Vista previa")
        lbl.setFont(f)
        der.addWidget(lbl)

        self.lbl_desborda = QLabel(
            "⚠ El texto no cabe en una sola página. Acorta la lista de documentos o las notas.")
        self.lbl_desborda.setStyleSheet(
            "color:#8A2C0D; background:#FBE4D8; padding:6px; border-radius:4px;")
        self.lbl_desborda.setWordWrap(True)
        self.lbl_desborda.setVisible(False)
        der.addWidget(self.lbl_desborda)

        self.preview = PreviewPanel()
        der.addWidget(self.preview, 1)
        splitter.addWidget(der_widget)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 900])

        # Timer para no regenerar en cada tecla
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._actualizar_preview)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        QTimer.singleShot(0, self._actualizar_preview)
        if not self._comprobacion_inicial_hecha:
            self._comprobacion_inicial_hecha = True
            QTimer.singleShot(3000, lambda: comprobar_actualizaciones(self, __version__, silencioso=True))

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

    def _aplicar_periodo_sugerido(self) -> None:
        clave, anio = T.periodo_sugerido_hoy()
        self._set_periodo(clave)
        self.spin_anio.setValue(anio)

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
        self._actualizar_aviso_fecha()
        self._programar_preview()

    def _on_fecha_cambia(self) -> None:
        self._actualizar_aviso_fecha()
        self._programar_preview()

    def _actualizar_aviso_fecha(self) -> None:
        qd = self.date_limite.date()
        d = date(qd.year(), qd.month(), qd.day())
        aviso = T.aviso_fecha(d)
        self.lbl_aviso_fecha.setText(f"⚠ {aviso}" if aviso else "")

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

    def _refrescar_completer_clientes(self) -> None:
        nombres = [c.nombre for c in C.cargar()]
        modelo = QStringListModel(nombres, self)
        completer = QCompleter(modelo, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.txt_cliente.setCompleter(completer)

    # -------------------------------------------------------------- preview
    def _programar_preview(self) -> None:
        self._timer.start()

    def _actualizar_preview(self) -> None:
        ctx = self._contexto()
        plantilla = self._plantilla_actual()

        def generador(dpi, info):
            return render_preview(ctx, plantilla, dpi=dpi, info=info)

        info = self.preview.mostrar(generador)
        self.lbl_desborda.setVisible(bool(info.get("desborda")))

    # ----------------------------------------------------------------- PDF
    def _guardar_pdf(self) -> None:
        ctx = self._contexto()
        plantilla = self._plantilla_actual()
        escritorio = Path.home() / "Desktop"
        escritorio.mkdir(parents=True, exist_ok=True)
        destino = ruta_sin_colision(escritorio, nombre_archivo(plantilla, ctx))

        info: dict = {}
        try:
            render_pdf(ctx, plantilla, destino, info=info)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{e}")
            return

        H.registrar(plantilla.nombre, ctx.periodo_corto, ctx.anio, ctx.cliente, str(destino))
        if C.asegurar_cliente(ctx.cliente):
            self._refrescar_completer_clientes()

        mensaje = f"Aviso guardado en el Escritorio:\n{destino.name}"
        if info.get("desborda"):
            mensaje += "\n\n⚠ Aviso: el texto no cabía en una sola página; revisa el PDF."
        resp = QMessageBox.question(
            self, "PDF generado", mensaje + "\n\n¿Abrir el archivo?",
            QMessageBox.Yes | QMessageBox.No)
        if resp == QMessageBox.Yes:
            try:
                os.startfile(str(destino))  # type: ignore[attr-defined]
            except Exception:
                pass

    # ------------------------------------------------------------ herramientas
    def _abrir_clientes(self) -> None:
        ClientesDialog(self).exec()
        self._refrescar_completer_clientes()

    def _abrir_lote(self) -> None:
        dlg = LoteDialog(self, self._contexto(), self._plantilla_actual(), self._ultima_carpeta())
        dlg.exec()
        self._guardar_ajustes(Path(dlg.carpeta_usada()))
        self._refrescar_completer_clientes()

    def _abrir_historial(self) -> None:
        HistorialDialog(self).exec()

    def _abrir_editor_plantillas(self) -> None:
        if self._editor_plantillas is None or not self._editor_plantillas.isVisible():
            self._editor_plantillas = PlantillaEditorDialog(
                self, on_cambio=self._actualizar_preview)
        self._editor_plantillas.show()
        self._editor_plantillas.raise_()
        self._editor_plantillas.activateWindow()

    def _abrir_formato(self) -> None:
        if self._editor_formato is None or not self._editor_formato.isVisible():
            self._editor_formato = FormatoDialog(self, on_cambio=self._actualizar_preview)
        self._editor_formato.show()
        self._editor_formato.raise_()
        self._editor_formato.activateWindow()

    def _buscar_actualizaciones_manual(self) -> None:
        comprobar_actualizaciones(self, __version__, silencioso=False)

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
