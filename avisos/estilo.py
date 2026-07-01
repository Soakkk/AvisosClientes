"""Formato del documento (fuente, tamano e interlineado), configurable
por el usuario al estilo Word y guardado para que se aplique a todos los
avisos futuros."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from . import config

FUENTE_DEF = "Georgia"
TAMANO_CUERPO_DEF = 11.0
INTERLINEADO_DEF = 120.0   # porcentaje
ESPACIO_PARRAFO_DEF = 8.0  # puntos


@dataclass
class Estilo:
    fuente: str = FUENTE_DEF
    tamano_cuerpo: float = TAMANO_CUERPO_DEF
    interlineado: float = INTERLINEADO_DEF
    espacio_parrafo: float = ESPACIO_PARRAFO_DEF


def _ruta():
    return config.config_dir() / "estilo.json"


def cargar() -> Estilo:
    try:
        datos = json.loads(_ruta().read_text("utf-8"))
        return Estilo(**datos)
    except Exception:
        return Estilo()


def guardar(estilo: Estilo) -> None:
    _ruta().write_text(json.dumps(asdict(estilo), ensure_ascii=False, indent=2), "utf-8")


def restablecer() -> Estilo:
    estilo = Estilo()
    guardar(estilo)
    return estilo
