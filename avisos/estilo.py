"""Formato del documento (fuente, tamano e interlineado), configurable
por el usuario al estilo Word y guardado para que se aplique a todos los
avisos futuros."""
from __future__ import annotations

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
    datos = config.leer_json(_ruta(), None)
    try:
        return Estilo(**datos) if datos else Estilo()
    except Exception:
        return Estilo()


def guardar(estilo: Estilo) -> None:
    config.escribir_json(_ruta(), asdict(estilo))


def restablecer() -> Estilo:
    estilo = Estilo()
    guardar(estilo)
    return estilo
