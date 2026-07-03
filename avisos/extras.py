"""Documentacion opcional reutilizable: bloques de documentos (con un
nombre) que se guardan una vez y se pueden anadir o quitar con un clic,
en cualquier tipo de aviso. Cada bloque se inserta como su propio
parrafo (con una frase introductoria opcional) y su propia lista, sin
mezclarse con la lista de documentos base."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from . import config


@dataclass
class Extra:
    etiqueta: str
    intro: str = ""             # frase antes de la lista, opcional
    lineas: list[str] = field(default_factory=list)


def _ruta():
    return config.config_dir() / "extras_documentos.json"


def cargar() -> list[Extra]:
    datos = config.leer_json(_ruta(), [])
    try:
        return [Extra(**d) for d in datos]
    except Exception:
        return []


def guardar(extras: list[Extra]) -> None:
    ordenados = sorted(extras, key=lambda e: e.etiqueta.lower())
    config.escribir_json(_ruta(), [asdict(e) for e in ordenados])


def upsert(extras: list[Extra], nuevo: Extra, etiqueta_original: str = "") -> list[Extra]:
    """Anade `nuevo`, sustituyendo cualquier entrada con el mismo nombre
    (o con `etiqueta_original`, si se esta editando y el nombre cambio)."""
    clave = (etiqueta_original or nuevo.etiqueta).strip().lower()
    restantes = [e for e in extras if e.etiqueta.strip().lower() != clave]
    restantes.append(nuevo)
    return restantes


def eliminar(extras: list[Extra], etiqueta: str) -> list[Extra]:
    clave = etiqueta.strip().lower()
    return [e for e in extras if e.etiqueta.strip().lower() != clave]
