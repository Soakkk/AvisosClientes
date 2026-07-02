"""Ventana principal del generador de avisos."""
from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

from PySide6.QtCore import QDate, QStringListModel, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QTextListFormat
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QDateEdit, QFormLayout, QFrame,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSpinBox, QSplitter, QTabWidget, QTextEdit, QToolButton, QVBoxLayout,
    QWidget,
)

from . import __version__
from . import clients as C
from . import config
from . import estilo as E
from . import extras as X
from . import history as H
from . import render as R
from . import templates as T
from .ui.actualizaciones import comprobar_actualizaciones
from .ui.clientes import ClientesDialog
from .ui.extras import ExtrasDialog
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

        self._docs_tocados = False       # el usuario edito la lista de documentos
        self._editor_dirty = False       # el usuario edito el texto del aviso a mano
        self._cargando_editor = False    # evita marcar dirty al cargar por codigo
        self._editor_plantillas: PlantillaEditorDialog | None = None
        self._editor_formato: FormatoDialog | None = None
        self._comprobacion_inicial_hecha = False

        self._construir_menu()
        self._construir_ui()
        self._aplicar_periodo_sugerido()
        self._cargar_ajustes()
        self._refrescar_completer_clientes()
        self._refrescar_lista_extras()
        self._on_plantilla_cambia(forzar_docs=True)
        self._regenerar_editor()

    # ------------------------------------------------------------------ menu
    def _construir_menu(self) -> None:
        menu = self.menuBar().addMenu("Herramientas")
        menu.addAction("Clientes…", self._abrir_clientes)
        menu.addAction("Generar para varios clientes…", self._abrir_lote)
        menu.addAction("Historial de avisos…", self._abrir_historial)
        menu.addSeparator()
        menu.addAction("Editar plantillas…", self._abrir_editor_plantillas)
        menu.addAction("Formato del documento…", self._abrir_formato)
        menu.addAction("Documentación opcional…", self._abrir_extras)

        ayuda = self.menuBar().addMenu("Ayuda")
        ayuda.addAction("Buscar actualizaciones…", self._buscar_actualizaciones_manual)

    # ------------------------------------------------------------------ UI
    def _construir_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QVBoxLayout(central)
        raiz.setContentsMargins(14, 14, 14, 14)

        splitter = QSplitter(Qt.Horizontal)
        raiz.addWidget(splitter)

        splitter.addWidget(self._construir_formulario())
        splitter.addWidget(self._construir_editor())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([420, 940])

        # Timer para no regenerar la vista previa en cada tecla
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._actualizar_preview)

    def _construir_formulario(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(300)
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
        self.txt_cliente.textChanged.connect(self._al_cambiar_datos)
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
        self.chk_navidad.stateChanged.connect(self._al_cambiar_datos)
        ly_d.addRow("", self.chk_navidad)

        col.addWidget(gb_d)

        gb_doc = QGroupBox("Documentos solicitados (uno por línea)")
        ly_doc = QVBoxLayout(gb_doc)
        self.txt_docs = QPlainTextEdit()
        self.txt_docs.setMinimumHeight(100)
        self.txt_docs.textChanged.connect(self._on_docs_editados)
        ly_doc.addWidget(self.txt_docs)
        btn_reset = QPushButton("Restablecer lista de la plantilla")
        btn_reset.clicked.connect(self._reset_docs)
        ly_doc.addWidget(btn_reset)

        ly_doc.addWidget(QLabel("Añadir documentación opcional:"))
        self.lista_extras = QListWidget()
        self.lista_extras.setMaximumHeight(90)
        self.lista_extras.itemChanged.connect(self._on_extra_marcado)
        ly_doc.addWidget(self.lista_extras)
        btn_gestionar_extras = QPushButton("Gestionar documentación opcional…")
        btn_gestionar_extras.clicked.connect(self._abrir_extras)
        ly_doc.addWidget(btn_gestionar_extras)

        col.addWidget(gb_doc)

        gb_n = QGroupBox("Notas adicionales (opcional)")
        ly_n = QVBoxLayout(gb_n)
        self.txt_notas = QPlainTextEdit()
        self.txt_notas.setMaximumHeight(70)
        self.txt_notas.textChanged.connect(self._al_cambiar_datos)
        ly_n.addWidget(self.txt_notas)
        col.addWidget(gb_n)

        self.btn_pdf = QPushButton("Generar y guardar PDF en el Escritorio")
        self.btn_pdf.setMinimumHeight(40)
        self.btn_pdf.clicked.connect(self._guardar_pdf)
        col.addWidget(self.btn_pdf)
        col.addStretch(1)

        return form_scroll

    def _construir_editor(self) -> QWidget:
        contenedor = QWidget()
        lay = QVBoxLayout(contenedor)
        lay.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()

        # --- Pestana "Documento" (editable) ---
        doc_tab = QWidget()
        doc_lay = QVBoxLayout(doc_tab)
        doc_lay.setContentsMargins(0, 0, 0, 0)

        # Aviso de "datos cambiados" cuando el texto esta editado a mano
        self.banner_datos = QWidget()
        bl = QHBoxLayout(self.banner_datos)
        bl.setContentsMargins(8, 4, 8, 4)
        lbl_banner = QLabel("Has editado el texto a mano. Si quieres aplicar los "
                            "datos del formulario, se reescribirá el aviso.")
        lbl_banner.setWordWrap(True)
        btn_actualizar = QPushButton("Reescribir con el formulario")
        btn_actualizar.clicked.connect(self._regenerar_editor)
        bl.addWidget(lbl_banner, 1)
        bl.addWidget(btn_actualizar)
        self.banner_datos.setStyleSheet("background:#FBF3DD; border:1px solid #E4D6A8;")
        self.banner_datos.setVisible(False)
        doc_lay.addWidget(self.banner_datos)

        doc_lay.addLayout(self._construir_barra_formato())

        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.setStyleSheet(
            "QTextEdit{background:#FFFFFF; border:1px solid #C9C2AC; padding:22px;}")
        self.editor.textChanged.connect(self._on_editor_cambiado)
        self.editor.cursorPositionChanged.connect(self._sincronizar_barra_formato)
        doc_lay.addWidget(self.editor, 1)

        pista = QLabel("El logo y el pie de página se añaden automáticamente al PDF. "
                       "Puedes editar el texto libremente (líneas, espacios, negrita…).")
        pista.setStyleSheet("color:#777; font-size:11px;")
        pista.setWordWrap(True)
        doc_lay.addWidget(pista)

        self.tabs.addTab(doc_tab, "Documento")

        # --- Pestana "Vista previa PDF" ---
        prev_tab = QWidget()
        prev_lay = QVBoxLayout(prev_tab)
        prev_lay.setContentsMargins(0, 0, 0, 0)
        self.lbl_desborda = QLabel(
            "⚠ El texto no cabe en una sola página. Acorta el texto o reduce el "
            "tamaño de letra en Herramientas → Formato del documento.")
        self.lbl_desborda.setStyleSheet(
            "color:#8A2C0D; background:#FBE4D8; padding:6px; border-radius:4px;")
        self.lbl_desborda.setWordWrap(True)
        self.lbl_desborda.setVisible(False)
        prev_lay.addWidget(self.lbl_desborda)
        self.preview = PreviewPanel()
        prev_lay.addWidget(self.preview, 1)
        self.tabs.addTab(prev_tab, "Vista previa PDF")

        self.tabs.currentChanged.connect(self._on_tab_cambia)
        lay.addWidget(self.tabs)
        return contenedor

    def _construir_barra_formato(self) -> QHBoxLayout:
        barra = QHBoxLayout()
        barra.setSpacing(4)

        def boton(texto, tooltip, slot, checkable=False):
            b = QToolButton()
            b.setText(texto)
            b.setToolTip(tooltip)
            b.setCheckable(checkable)
            b.clicked.connect(slot)
            barra.addWidget(b)
            return b

        fb = QFont()
        fb.setBold(True)
        self.btn_negrita = boton("N", "Negrita (Ctrl+B)", self._fmt_negrita, checkable=True)
        self.btn_negrita.setFont(fb)
        fi = QFont()
        fi.setItalic(True)
        self.btn_cursiva = boton("C", "Cursiva (Ctrl+I)", self._fmt_cursiva, checkable=True)
        self.btn_cursiva.setFont(fi)
        boton("• Lista", "Lista con viñetas", self._fmt_lista)
        barra.addSpacing(10)
        boton("⯇", "Alinear a la izquierda", lambda: self.editor.setAlignment(Qt.AlignLeft))
        boton("≡", "Centrar", lambda: self.editor.setAlignment(Qt.AlignHCenter))
        barra.addStretch(1)

        btn_guardar_def = QPushButton("Guardar como predeterminado")
        btn_guardar_def.setToolTip("Convierte este texto en el texto base para todos los "
                                   "futuros avisos de este tipo (los datos se seguirán "
                                   "rellenando solos)")
        btn_guardar_def.clicked.connect(self._guardar_como_predeterminado)
        barra.addWidget(btn_guardar_def)

        btn_restaurar = QPushButton("Restaurar texto de la plantilla")
        btn_restaurar.setToolTip("Vuelve al texto predefinido con los datos actuales del formulario")
        btn_restaurar.clicked.connect(self._restaurar_texto)
        barra.addWidget(btn_restaurar)
        return barra

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
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
            documentos_extra=self._extras_marcados(),
            navidad=self.chk_navidad.isChecked(),
            notas=self.txt_notas.toPlainText(),
        )

    def _extras_marcados(self) -> list[tuple[str, list[str]]]:
        if not hasattr(self, "lista_extras"):
            return []
        disponibles = {e.etiqueta: e for e in X.cargar()}
        activos = []
        for i in range(self.lista_extras.count()):
            item = self.lista_extras.item(i)
            if item.checkState() == Qt.Checked and item.text() in disponibles:
                extra = disponibles[item.text()]
                activos.append((extra.intro, extra.lineas))
        return activos

    def _aplicar_periodo_sugerido(self) -> None:
        clave, anio = T.periodo_sugerido_hoy()
        self._set_periodo(clave)
        self.spin_anio.blockSignals(True)
        self.spin_anio.setValue(anio)
        self.spin_anio.blockSignals(False)
        self._actualizar_fecha_desde_periodo()

    def _on_plantilla_cambia(self, forzar_docs: bool = True) -> None:
        p = self._plantilla_actual()
        self.chk_navidad.setVisible(p.usa_navidad)
        if p.id == "cierre_anual":
            self._set_periodo("4T")
        if forzar_docs:
            self._set_docs(p.documentos_def)
        self._actualizar_fecha_desde_periodo()
        self._al_cambiar_datos()

    def _actualizar_fecha_desde_periodo(self) -> None:
        clave = self.cmb_periodo.currentData()
        d = T.plazo_por_defecto(clave, self.spin_anio.value())
        self.date_limite.blockSignals(True)
        self.date_limite.setDate(QDate(d.year, d.month, d.day))
        self.date_limite.blockSignals(False)
        self._actualizar_aviso_fecha()

    def _on_periodo_cambia(self) -> None:
        self._actualizar_fecha_desde_periodo()
        self._al_cambiar_datos()

    def _on_fecha_cambia(self) -> None:
        self._actualizar_aviso_fecha()
        self._al_cambiar_datos()

    def _actualizar_aviso_fecha(self) -> None:
        qd = self.date_limite.date()
        d = date(qd.year(), qd.month(), qd.day())
        aviso = T.aviso_fecha(d)
        self.lbl_aviso_fecha.setText(f"⚠ {aviso}" if aviso else "")

    def _on_docs_editados(self) -> None:
        self._docs_tocados = True
        self._al_cambiar_datos()

    def _set_docs(self, docs: list[str]) -> None:
        self.txt_docs.blockSignals(True)
        self.txt_docs.setPlainText("\n".join(docs))
        self.txt_docs.blockSignals(False)
        self._docs_tocados = False
        self._desmarcar_extras()

    def _reset_docs(self) -> None:
        self._set_docs(self._plantilla_actual().documentos_def)
        self._al_cambiar_datos()

    # ------------------------------------------------------- doc. opcional
    def _refrescar_lista_extras(self) -> None:
        marcados = {self.lista_extras.item(i).text()
                   for i in range(self.lista_extras.count())
                   if self.lista_extras.item(i).checkState() == Qt.Checked} \
            if hasattr(self, "lista_extras") else set()
        self.lista_extras.blockSignals(True)
        self.lista_extras.clear()
        for extra in sorted(X.cargar(), key=lambda e: e.etiqueta.lower()):
            item = QListWidgetItem(extra.etiqueta)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if extra.etiqueta in marcados else Qt.Unchecked)
            resumen = (f"{extra.intro}\n" if extra.intro else "") + "\n".join(f"• {ln}" for ln in extra.lineas)
            item.setToolTip(resumen)
            self.lista_extras.addItem(item)
        self.lista_extras.blockSignals(False)

    def _desmarcar_extras(self) -> None:
        if not hasattr(self, "lista_extras"):
            return
        self.lista_extras.blockSignals(True)
        for i in range(self.lista_extras.count()):
            self.lista_extras.item(i).setCheckState(Qt.Unchecked)
        self.lista_extras.blockSignals(False)

    def _on_extra_marcado(self, item: QListWidgetItem) -> None:
        # La documentacion opcional se guarda aparte (T.Contexto.documentos_extra)
        # y se inserta como su propio parrafo/lista: no se mezcla con la
        # lista base de "Documentos solicitados".
        self._al_cambiar_datos()

    def _abrir_extras(self) -> None:
        ExtrasDialog(self).exec()
        self._refrescar_lista_extras()

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

    # --------------------------------------------------------------- editor
    def _al_cambiar_datos(self) -> None:
        """Un dato del formulario ha cambiado. Si el texto no se ha tocado
        a mano, se reescribe con los nuevos datos; si se ha editado, se
        avisa (sin pisar lo que el usuario escribio)."""
        if not hasattr(self, "editor"):
            return
        if self._editor_dirty:
            self.banner_datos.setVisible(True)
        else:
            self._regenerar_editor()

    def _regenerar_editor(self) -> None:
        est = E.cargar()
        self._cargando_editor = True
        f = QFont(est.fuente)
        f.setPointSizeF(est.tamano_cuerpo)
        self.editor.document().setDefaultFont(f)
        self.editor.document().setDefaultStyleSheet(R.stylesheet(est))
        self.editor.setHtml(R.documento_inicial(self._contexto(), self._plantilla_actual(), est))
        R.aplicar_margenes_bloques(self.editor.document(), est)
        self._cargando_editor = False
        self._editor_dirty = False
        self.banner_datos.setVisible(False)
        self._programar_preview()

    def _restaurar_texto(self) -> None:
        if self._editor_dirty:
            resp = QMessageBox.question(
                self, "Restaurar texto",
                "Se descartarán los cambios que hayas hecho a mano y se volverá "
                "al texto de la plantilla con los datos actuales. ¿Continuar?",
                QMessageBox.Yes | QMessageBox.No)
            if resp != QMessageBox.Yes:
                return
        self._regenerar_editor()

    def _guardar_como_predeterminado(self) -> None:
        p = self._plantilla_actual()
        ctx = self._contexto()
        mensaje = (
            f"Se guardará el texto actual como el texto base de «{p.nombre}», "
            "para todos los avisos futuros de este tipo.\n\n"
            "Los datos de cliente, periodo y fecha se seguirán rellenando "
            "automáticamente. Podrás revisarlo o deshacerlo en "
            "Herramientas → Editar plantillas.")
        if ctx.documentos_extra:
            mensaje += ("\n\n⚠ Tienes documentación opcional marcada. No se incluirá en el "
                        "texto base guardado (la documentación opcional sigue siendo "
                        "opcional, se añade aparte en cada aviso).")
        resp = QMessageBox.question(
            self, "Guardar como predeterminado", mensaje + "\n\n¿Continuar?",
            QMessageBox.Yes | QMessageBox.No)
        if resp != QMessageBox.Yes:
            return
        try:
            titulo, cuerpo = R.documento_a_plantilla(self.editor.document(), ctx)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el texto:\n{e}")
            return
        if not titulo.strip() or not cuerpo.strip():
            QMessageBox.warning(self, "No se pudo guardar",
                                 "El documento parece estar vacío.")
            return
        T.guardar_override(p.id, titulo, cuerpo)
        self._editor_dirty = False
        self.banner_datos.setVisible(False)
        QMessageBox.information(
            self, "Guardado",
            f"Guardado como texto predeterminado de «{p.nombre}».\n"
            "Se usará en los próximos avisos de este tipo.")

    def _on_editor_cambiado(self) -> None:
        if self._cargando_editor:
            return
        self._editor_dirty = True
        self._programar_preview()

    # --- barra de formato ---
    def _fmt_negrita(self) -> None:
        peso = QFont.Normal if self.editor.fontWeight() > QFont.Normal else QFont.Bold
        self.editor.setFontWeight(peso)
        self.editor.setFocus()

    def _fmt_cursiva(self) -> None:
        self.editor.setFontItalic(not self.editor.fontItalic())
        self.editor.setFocus()

    def _fmt_lista(self) -> None:
        self.editor.textCursor().createList(QTextListFormat.ListDisc)
        self.editor.setFocus()

    def _sincronizar_barra_formato(self) -> None:
        self.btn_negrita.setChecked(self.editor.fontWeight() > QFont.Normal)
        self.btn_cursiva.setChecked(self.editor.fontItalic())

    def keyPressEvent(self, event) -> None:  # noqa: N802 (atajos Ctrl+B / Ctrl+I)
        if event.modifiers() & Qt.ControlModifier and self.editor.hasFocus():
            if event.key() == Qt.Key_B:
                self._fmt_negrita()
                return
            if event.key() == Qt.Key_I:
                self._fmt_cursiva()
                return
        super().keyPressEvent(event)

    # -------------------------------------------------------------- preview
    def _on_tab_cambia(self, indice: int) -> None:
        if self.tabs.tabText(indice).startswith("Vista"):
            self._actualizar_preview()

    def _programar_preview(self) -> None:
        self._timer.start()

    def _actualizar_preview(self) -> None:
        if not hasattr(self, "preview"):
            return
        html = self.editor.toHtml()

        def generador(dpi, info):
            return R.render_preview_documento(html, dpi=dpi, info=info, est=E.cargar())

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
            R.render_pdf_documento(self.editor.toHtml(), destino, info=info, est=E.cargar())
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
            self._editor_plantillas = PlantillaEditorDialog(self, on_cambio=self._al_cambiar_desde_dialogo)
        self._editor_plantillas.show()
        self._editor_plantillas.raise_()
        self._editor_plantillas.activateWindow()

    def _abrir_formato(self) -> None:
        if self._editor_formato is None or not self._editor_formato.isVisible():
            self._editor_formato = FormatoDialog(self, on_cambio=self._al_cambiar_desde_dialogo)
        self._editor_formato.show()
        self._editor_formato.raise_()
        self._editor_formato.activateWindow()

    def _al_cambiar_desde_dialogo(self) -> None:
        """Cambio hecho en el editor de plantillas o de formato: si el texto
        no se ha tocado a mano, se reescribe con lo nuevo; si se ha editado,
        se deja como esta (para no perder los cambios) y solo se avisa."""
        if self._editor_dirty:
            self.banner_datos.setVisible(True)
            self._programar_preview()
        else:
            self._regenerar_editor()

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
                self.cmb_plantilla.blockSignals(True)
                self.cmb_plantilla.setCurrentIndex(idx)
                self.cmb_plantilla.blockSignals(False)

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
