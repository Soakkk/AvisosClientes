"""Historial de avisos generados (para consultar que se genero y cuando)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from . import config

_MAX_ENTRADAS = 500


@dataclass
class Entrada:
    fecha_hora: str
    plantilla: str
    periodo: str
    anio: int
    cliente: str
    ruta: str


def _ruta() -> Path:
    return config.config_dir() / "historial.json"


def cargar() -> list[Entrada]:
    datos = config.leer_json(_ruta(), [])
    try:
        return [Entrada(**d) for d in datos]
    except Exception:
        return []


def registrar(plantilla: str, periodo: str, anio: int, cliente: str, ruta: str) -> None:
    entradas = cargar()
    entradas.append(Entrada(
        fecha_hora=datetime.now().strftime("%d/%m/%Y %H:%M"),
        plantilla=plantilla,
        periodo=periodo,
        anio=anio,
        cliente=cliente.strip() or "(genérico)",
        ruta=str(ruta),
    ))
    entradas = entradas[-_MAX_ENTRADAS:]
    config.escribir_json(_ruta(), [asdict(e) for e in entradas])
