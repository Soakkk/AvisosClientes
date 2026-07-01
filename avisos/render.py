"""Composicion y render del aviso (vista previa e impresion a PDF).

Una unica rutina `pintar_pagina` dibuja el aviso completo, y se usa tanto
para la vista previa (a QImage) como para el PDF (a QPrinter). Asi lo que
se ve en pantalla es exactamente lo que sale en el PDF.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, Qt, QSizeF
from PySide6.QtGui import (
    QColor, QFont, QImage, QPageLayout, QPageSize, QPainter, QTextDocument,
)
from PySide6.QtPrintSupport import QPrinter

from . import config
from . import estilo as E
from .templates import Contexto, Plantilla, render_cuerpo, render_titulo

# A4 en mm
A4_W_MM, A4_H_MM = 210.0, 297.0
# Margenes (mm)
MARGEN_X = 20.0
MARGEN_SUP = 16.0
MARGEN_INF = 16.0

# Tamanos del titulo y el pie de pagina, como diferencia respecto al
# tamano de letra del cuerpo (configurable por el usuario), para que todo
# escale junto de forma proporcional.
DELTA_TITULO = 4.5
DELTA_PIE_NEGRITA = -2.0
DELTA_PIE_NORMAL = -2.5

# QTextDocument, cuando no esta asociado a un dispositivo concreto, siempre
# interpreta sus medidas (textWidth, tamanos de fuente) como si el destino
# tuviera 96 DPI - da igual la resolucion real del QPrinter/QImage donde
# se pinte despues. Si no se compensa esa diferencia, en un QPrinter a
# alta resolucion (p. ej. 1200 DPI) el cuerpo del texto sale minusculo.
_QTEXTDOCUMENT_DPI = 96.0


def _mm(px_per_mm: float, mm: float) -> float:
    return mm * px_per_mm


def _doc_cuerpo(html: str, ancho_px: float, est: E.Estilo) -> QTextDocument:
    doc = QTextDocument()
    doc.setDocumentMargin(0)
    f = QFont(est.fuente)
    f.setPointSizeF(est.tamano_cuerpo)
    doc.setDefaultFont(f)
    doc.setTextWidth(ancho_px)
    doc.setDefaultStyleSheet(
        f"p{{color:{config.INK};line-height:{est.interlineado}%;"
        f"margin:{est.espacio_parrafo}pt 0;}}"
        f"li{{color:{config.INK};margin:2pt 0;}}"
        f"b{{color:{config.GREEN_SOFT};}}"
    )
    doc.setHtml(html)
    return doc


def pintar_pagina(painter: QPainter, ancho_px: float, alto_px: float,
                  res_dpi: float, titulo: str, cuerpo_html: str,
                  info: dict | None = None, est: E.Estilo | None = None) -> None:
    """Dibuja el aviso completo dentro de un area ancho_px x alto_px.

    `titulo` y `cuerpo_html` ya vienen resueltos (placeholders sustituidos).
    Si se pasa `info`, se rellena con info["desborda"] = True/False segun
    si el cuerpo del texto cabe en el espacio disponible de la pagina.
    Si no se pasa `est` (fuente/tamano/interlineado), se usa el guardado
    por el usuario (o el de fabrica si no ha configurado nada).
    """
    est = est or E.cargar()
    ppm = res_dpi / 25.4  # pixeles por mm
    fuente = est.fuente

    x0 = _mm(ppm, MARGEN_X)
    content_w = ancho_px - 2 * x0
    y = _mm(ppm, MARGEN_SUP)

    # Fondo blanco
    painter.fillRect(QRectF(0, 0, ancho_px, alto_px), QColor("#FFFFFF"))

    # --- Logo (centrado) ---
    logo = QImage(str(config.logo_path()))
    if not logo.isNull():
        target_w = content_w * 0.56
        escala = logo.scaledToWidth(int(target_w), Qt.SmoothTransformation)
        lx = (ancho_px - escala.width()) / 2.0
        painter.drawImage(QRectF(lx, y, escala.width(), escala.height()), escala)
        y += escala.height() + _mm(ppm, 5)

    # --- Linea dorada ---
    painter.fillRect(QRectF(x0, y, content_w, _mm(ppm, 0.7)), QColor(config.GOLD))
    y += _mm(ppm, 7)

    # --- Titulo ---
    ft = QFont(fuente)
    ft.setPointSizeF(est.tamano_cuerpo + DELTA_TITULO)
    ft.setBold(True)
    painter.setFont(ft)
    painter.setPen(QColor(config.GREEN))
    rect_titulo = QRectF(x0, y, content_w, _mm(ppm, 40))
    flags = int(Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap)
    br = painter.boundingRect(rect_titulo, flags, titulo)
    painter.drawText(rect_titulo, flags, titulo)
    y += br.height() + _mm(ppm, 6)

    # --- Pie de pagina: se calcula antes para saber el hueco disponible ---
    pie_y = alto_px - _mm(ppm, MARGEN_INF) - _mm(ppm, 13)

    # --- Cuerpo (QTextDocument) ---
    # QTextDocument razona en "unidades a 96 DPI"; hay que pintarlo con el
    # painter escalado a esa referencia para que el tamano de letra salga
    # correcto sea cual sea la resolucion real del dispositivo (pantalla o
    # impresora/PDF).
    escala_doc = res_dpi / _QTEXTDOCUMENT_DPI
    content_w_doc = content_w / escala_doc
    alto_disponible_doc = (alto_px - y) / escala_doc

    doc = _doc_cuerpo(cuerpo_html, content_w_doc, est)
    if info is not None:
        info["desborda"] = (doc.size().height() * escala_doc) > (pie_y - y)
    painter.save()
    painter.translate(x0, y)
    painter.scale(escala_doc, escala_doc)
    doc.drawContents(painter, QRectF(0, 0, content_w_doc, alto_disponible_doc))
    painter.restore()

    # --- Pie de pagina (anclado abajo) ---
    painter.fillRect(QRectF(x0, pie_y, content_w, _mm(ppm, 0.5)), QColor(config.GOLD))
    pie_y += _mm(ppm, 2.5)

    fp_bold = QFont(fuente)
    fp_bold.setPointSizeF(est.tamano_cuerpo + DELTA_PIE_NEGRITA)
    fp_bold.setBold(True)
    fp = QFont(fuente)
    fp.setPointSizeF(est.tamano_cuerpo + DELTA_PIE_NORMAL)
    painter.setPen(QColor(config.GREEN))

    lineas = [
        (fp_bold, config.COMPANY_TITULARES),
        (fp, f"{config.COMPANY_DIRECCION} · {config.COMPANY_TELEFONOS}"),
        (fp, config.COMPANY_EMAIL),
    ]
    for fuente_linea, texto in lineas:
        painter.setFont(fuente_linea)
        r = QRectF(x0, pie_y, content_w, _mm(ppm, 5))
        painter.drawText(r, int(Qt.AlignHCenter | Qt.AlignTop), texto)
        pie_y += _mm(ppm, 4.2)


def render_preview_textos(titulo: str, cuerpo_html: str, dpi: float = 110.0,
                           info: dict | None = None, est: E.Estilo | None = None) -> QImage:
    """Devuelve una QImage A4 a partir de un titulo y un cuerpo ya resueltos.

    Se usa en el editor de plantillas y el editor de formato para
    previsualizar cambios todavia sin guardar.
    """
    ppm = dpi / 25.4
    w = int(round(A4_W_MM * ppm))
    h = int(round(A4_H_MM * ppm))
    img = QImage(w, h, QImage.Format_RGB32)
    img.fill(QColor("#FFFFFF"))
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    try:
        pintar_pagina(p, w, h, dpi, titulo, cuerpo_html, info=info, est=est)
    finally:
        p.end()
    return img


def render_preview(ctx: Contexto, plantilla: Plantilla, dpi: float = 110.0,
                    info: dict | None = None, est: E.Estilo | None = None) -> QImage:
    """Devuelve una QImage A4 con el aviso (para la vista previa)."""
    titulo = render_titulo(ctx, plantilla)
    cuerpo_html = render_cuerpo(ctx, plantilla)
    return render_preview_textos(titulo, cuerpo_html, dpi=dpi, info=info, est=est)


def render_pdf(ctx: Contexto, plantilla: Plantilla, ruta: str | Path,
                info: dict | None = None, est: E.Estilo | None = None) -> None:
    """Genera el PDF del aviso en `ruta`."""
    titulo = render_titulo(ctx, plantilla)
    cuerpo_html = render_cuerpo(ctx, plantilla)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(str(ruta))
    printer.setPageSize(QPageSize(QPageSize.A4))
    printer.setFullPage(True)
    printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter)

    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError("No se pudo iniciar la impresion a PDF")
    try:
        res = printer.resolution()
        page = printer.pageRect(QPrinter.DevicePixel)
        pintar_pagina(painter, page.width(), page.height(), res, titulo, cuerpo_html,
                      info=info, est=est)
    finally:
        painter.end()
