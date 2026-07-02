"""Documentacion opcional reutilizable: bloques de documentos (con un
nombre) que se guardan una vez y se pueden anadir o quitar de la lista
de documentos solicitados con un clic, en cualquier tipo de aviso."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from . import config


@dataclass
class Extra:
    etiqueta: str
    lineas: list[str] = field(default_factory=list)


def _ruta():
    return config.config_dir() / "extras_documentos.json"


def cargar() -> list[Extra]:
    try:
        datos = json.loads(_ruta().read_text("utf-8"))
        return [Extra(**d) for d in datos]
    except Exception:
        return []


def guardar(extras: list[Extra]) -> None:
    ordenados = sorted(extras, key=lambda e: e.etiqueta.lower())
    _ruta().write_text(
        json.dumps([asdict(e) for e in ordenados], ensure_ascii=False, indent=2), "utf-8")


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
