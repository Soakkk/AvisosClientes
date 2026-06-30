"""Plantillas de avisos y utilidades de periodo.

Cada plantilla define un titulo y un cuerpo en HTML a partir de un
contexto (periodo, anio, cliente, fecha limite, documentos, etc.).
La redaccion procede de los avisos reales de la oficina.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Periodos disponibles: clave -> (etiqueta larga, corta, meses[0-based], mes/dia plazo, offset anio plazo)
PERIODOS = {
    "1T": {"largo": "1.er Trimestre", "corto": "1T", "meses": [0, 1, 2],
           "plazo": (4, 20), "anio_offset": 0},
    "2T": {"largo": "2.º Trimestre", "corto": "2T", "meses": [3, 4, 5],
           "plazo": (7, 20), "anio_offset": 0},
    "3T": {"largo": "3.er Trimestre", "corto": "3T", "meses": [6, 7, 8],
           "plazo": (10, 20), "anio_offset": 0},
    "4T": {"largo": "4.º Trimestre", "corto": "4T", "meses": [9, 10, 11],
           "plazo": (1, 20), "anio_offset": 1},
    "RENTA": {"largo": "Ejercicio (Renta)", "corto": "Renta", "meses": list(range(12)),
              "plazo": (6, 30), "anio_offset": 0},
}


def meses_texto(clave: str) -> str:
    info = PERIODOS[clave]
    ms = info["meses"]
    if len(ms) == 12:
        return "el ejercicio completo"
    return f"{MESES[ms[0]]}, {MESES[ms[1]]} y {MESES[ms[2]]}"


def meses_rango(clave: str) -> str:
    info = PERIODOS[clave]
    ms = info["meses"]
    if len(ms) == 12:
        return "enero–diciembre"
    return f"{MESES[ms[0]]}–{MESES[ms[2]]}"


def plazo_por_defecto(clave: str, anio: int) -> date:
    info = PERIODOS[clave]
    mes, dia = info["plazo"]
    return date(anio + info["anio_offset"], mes, dia)


def fecha_larga(d: date) -> str:
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# --- Contexto que reciben las plantillas --------------------------------
@dataclass
class Contexto:
    periodo: str = "1T"            # clave de PERIODOS
    anio: int = date.today().year
    cliente: str = ""              # vacio -> "Estimado/a cliente"
    fecha_limite: date | None = None
    documentos: list[str] = field(default_factory=list)
    navidad: bool = False
    notas: str = ""

    @property
    def periodo_largo(self) -> str:
        return PERIODOS[self.periodo]["largo"]

    @property
    def periodo_corto(self) -> str:
        return PERIODOS[self.periodo]["corto"]

    @property
    def saludo(self) -> str:
        nombre = self.cliente.strip()
        return f"Estimado/a {nombre}:" if nombre else "Estimado/a cliente:"

    @property
    def fecha_limite_txt(self) -> str:
        d = self.fecha_limite or plazo_por_defecto(self.periodo, self.anio)
        return fecha_larga(d)


def _lista_html(items: list[str]) -> str:
    lis = "".join(f"<li>{x.strip()}</li>" for x in items if x.strip())
    return f'<ul style="margin:6pt 0 6pt 0;">{lis}</ul>' if lis else ""


def _notas_html(ctx: Contexto) -> str:
    if not ctx.notas.strip():
        return ""
    parrafos = "".join(
        f"<p style='margin:6pt 0;'>{ln.strip()}</p>"
        for ln in ctx.notas.strip().splitlines() if ln.strip()
    )
    return parrafos


@dataclass
class Plantilla:
    id: str
    grupo: str
    nombre: str
    documentos_def: list[str]
    usa_navidad: bool
    titulo: Callable[[Contexto], str]
    cuerpo: Callable[[Contexto], str]


# ======================================================================
#  PLANTILLAS
# ======================================================================

def _t_solicitud_trim(ctx: Contexto) -> str:
    return f"Solicitud de documentación — {ctx.periodo_largo} de {ctx.anio}"


def _c_solicitud_trim(ctx: Contexto) -> str:
    return f"""
<p>{ctx.saludo}</p>
<p style="margin:8pt 0;">Con motivo de la presentación de los impuestos correspondientes
al <b>{ctx.periodo_largo.lower()} de {ctx.anio}</b>, le rogamos que nos remita la documentación
necesaria para poder preparar y presentar sus obligaciones fiscales dentro del plazo establecido.</p>
<p style="margin:8pt 0 2pt 0;">En concreto, necesitamos la siguiente documentación:</p>
{_lista_html(ctx.documentos)}
<p style="margin:8pt 0;">Le agradeceríamos que nos hiciera llegar toda la documentación
<b>antes del {ctx.fecha_limite_txt}</b>, con el fin de poder revisarla con tiempo suficiente
y presentar los impuestos dentro de plazo.</p>
{_notas_html(ctx)}
<p style="margin:8pt 0;">Agradecemos de antemano su colaboración y quedamos a su disposición
para cualquier consulta o aclaración.</p>
<p style="margin:14pt 0 0 0;">Reciba un cordial saludo.</p>
"""


def _t_recordatorio(ctx: Contexto) -> str:
    return f"Recordatorio de plazos — Cierre del {ctx.periodo_largo} de {ctx.anio}"


def _c_recordatorio(ctx: Contexto) -> str:
    return f"""
<p>{ctx.saludo}</p>
<p style="margin:8pt 0;">Le recordamos que el plazo de presentación de las liquidaciones
correspondientes al <b>{ctx.periodo_largo} de {ctx.anio}</b> es el siguiente:</p>
<table width="100%" cellpadding="5" cellspacing="0"
       style="border-collapse:collapse; margin:6pt 0;">
  <tr>
    <td style="border:1px solid {'#C9C2AC'}; background:#F3F0E6;"><b>Modalidad de presentación</b></td>
    <td style="border:1px solid {'#C9C2AC'}; background:#F3F0E6;"><b>Plazo límite</b></td>
  </tr>
  <tr>
    <td style="border:1px solid {'#C9C2AC'};">Resultado positivo con domiciliación</td>
    <td style="border:1px solid {'#C9C2AC'};">Hasta el 15 del mes de presentación</td>
  </tr>
  <tr>
    <td style="border:1px solid {'#C9C2AC'};">Resto de resultados (negativo, a compensar, aplazamiento)</td>
    <td style="border:1px solid {'#C9C2AC'};">Hasta el {ctx.fecha_limite_txt}</td>
  </tr>
</table>
<p style="margin:8pt 0 2pt 0;">Para poder confeccionar y presentar las liquidaciones en plazo,
le pedimos que nos haga llegar, cuanto antes, la documentación que se detalla a continuación:</p>
{_lista_html(ctx.documentos)}
{_notas_html(ctx)}
<p style="margin:8pt 0;">Sin otro particular, quedamos a su entera disposición para cualquier
consulta o aclaración que pudiera precisar.</p>
<p style="margin:14pt 0 0 0;">Reciba un cordial saludo.</p>
"""


def _t_cierre_anual(ctx: Contexto) -> str:
    return f"Solicitud de documentación — 4.º Trimestre y Resumen Anual {ctx.anio}"


def _c_cierre_anual(ctx: Contexto) -> str:
    navidad = (
        '<p style="margin:8pt 0;">Desde <b>Asesoría E. Marín</b> le deseamos una Feliz Navidad '
        'y un próspero año nuevo lleno de alegría, salud y felicidad.</p>'
        if ctx.navidad else ""
    )
    return f"""
<p>{ctx.saludo}</p>
{navidad}
<p style="margin:8pt 0;">Con motivo del cierre del ejercicio <b>{ctx.anio}</b>, le informamos de sus
próximas obligaciones fiscales. Para poder revisar su documentación y presentar sus impuestos
dentro de los plazos legales, necesitamos que nos remita la siguiente información:</p>
{_lista_html(ctx.documentos)}
<p style="margin:8pt 0;">Le agradeceríamos que nos remitiera la documentación
<b>antes del {ctx.fecha_limite_txt}</b>, con el fin de garantizar la presentación en plazo
de sus impuestos.</p>
{_notas_html(ctx)}
<p style="margin:8pt 0;">Quedamos a su disposición para cualquier duda o aclaración.</p>
<p style="margin:14pt 0 0 0;">Reciba un cordial saludo.</p>
"""


def _t_renta_arrend(ctx: Contexto) -> str:
    return f"Solicitud de información — Bienes arrendados · Renta {ctx.anio}"


def _c_renta_arrend(ctx: Contexto) -> str:
    return f"""
<p>{ctx.saludo}</p>
<p style="margin:8pt 0;">Con motivo de la preparación de su declaración de la Renta del ejercicio
<b>{ctx.anio}</b>, necesitamos que nos facilite la información relativa a los bienes que haya
tenido arrendados durante el año.</p>
<p style="margin:8pt 0 2pt 0;">De cada bien arrendado necesitamos lo siguiente:</p>
{_lista_html(ctx.documentos)}
<p style="margin:8pt 0;">Le rogamos que nos lo haga llegar <b>antes del {ctx.fecha_limite_txt}</b>
para poder preparar su declaración con tiempo suficiente.</p>
{_notas_html(ctx)}
<p style="margin:8pt 0;">Agradecemos de antemano su colaboración y quedamos a su disposición.</p>
<p style="margin:14pt 0 0 0;">Reciba un cordial saludo.</p>
"""


DOCS_TRIMESTRE = [
    "Facturas de ingresos y gastos, emitidas y recibidas, correspondientes al trimestre.",
    "Facturas o justificantes pendientes de trimestres anteriores, si quedara alguno por entregar.",
    "Facturas y documentación de compra o venta de bienes de inversión, si ha realizado alguna operación de este tipo.",
]

DOCS_CIERRE = [
    "Facturas de ingresos y gastos, emitidas y recibidas, correspondientes al 4.º trimestre.",
    "Facturas de trimestres anteriores que hayan quedado pendientes, para completar todo el ejercicio.",
    "Facturas y documentación técnica (fotocopia) de compra o venta de bienes de inversión o vehículos comerciales realizada durante el año.",
]

DOCS_RECORD = [
    "Facturas de ingresos (ventas / honorarios) del trimestre.",
    "Facturas de gastos deducibles correspondientes al mismo período.",
    "En caso de arrendamiento: facturas de alquiler y de los gastos asociados.",
    "Cualquier otra documentación contable o justificativa relevante.",
]

DOCS_RENTA = [
    "NIF del arrendatario.",
    "Ingresos percibidos durante el año por el arrendamiento.",
    "Gastos pagados del inmueble (IBI, seguros, comunidad, reparaciones, intereses de préstamo...).",
]


PLANTILLAS: list[Plantilla] = [
    Plantilla(
        id="solicitud_trim",
        grupo="Solicitud de documentación",
        nombre="Solicitud de documentación — Trimestre",
        documentos_def=DOCS_TRIMESTRE,
        usa_navidad=False,
        titulo=_t_solicitud_trim,
        cuerpo=_c_solicitud_trim,
    ),
    Plantilla(
        id="recordatorio",
        grupo="Solicitud de documentación",
        nombre="Recordatorio de plazos — Cierre de trimestre",
        documentos_def=DOCS_RECORD,
        usa_navidad=False,
        titulo=_t_recordatorio,
        cuerpo=_c_recordatorio,
    ),
    Plantilla(
        id="cierre_anual",
        grupo="Cierre de ejercicio",
        nombre="4.º Trimestre + Resumen Anual (cierre de ejercicio)",
        documentos_def=DOCS_CIERRE,
        usa_navidad=True,
        titulo=_t_cierre_anual,
        cuerpo=_c_cierre_anual,
    ),
    Plantilla(
        id="renta_arrend",
        grupo="Renta",
        nombre="Renta — Bienes arrendados",
        documentos_def=DOCS_RENTA,
        usa_navidad=False,
        titulo=_t_renta_arrend,
        cuerpo=_c_renta_arrend,
    ),
]


def por_id(pid: str) -> Plantilla:
    for p in PLANTILLAS:
        if p.id == pid:
            return p
    return PLANTILLAS[0]
