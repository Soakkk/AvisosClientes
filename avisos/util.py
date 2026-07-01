"""Utilidades pequenas compartidas (nombres de archivo)."""
from __future__ import annotations

import re
from pathlib import Path

from .templates import Contexto, Plantilla


def slug(texto: str) -> str:
    texto = texto.lower()
    repl = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
            "º": "", "ª": "", "·": "", ".": "", ",": ""}
    for k, v in repl.items():
        texto = texto.replace(k, v)
    texto = re.sub(r"[^a-z0-9]+", "_", texto).strip("_")
    return texto or "aviso"


def nombre_archivo(plantilla: Plantilla, ctx: Contexto) -> str:
    partes = [slug(plantilla.nombre), ctx.periodo_corto, str(ctx.anio)]
    if ctx.cliente.strip():
        partes.append(slug(ctx.cliente))
    return "AVISO_" + "_".join(partes).upper() + ".pdf"


def ruta_sin_colision(carpeta: Path, nombre: str) -> Path:
    """Ruta libre en `carpeta`: si `nombre` ya existe, anade (2), (3)... """
    candidato = carpeta / nombre
    if not candidato.exists():
        return candidato
    base = Path(nombre).stem
    ext = Path(nombre).suffix
    contador = 2
    while True:
        candidato = carpeta / f"{base} ({contador}){ext}"
        if not candidato.exists():
            return candidato
        contador += 1
