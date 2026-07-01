"""Base de datos de clientes (nombre, NIF, telefono, email).

Se guarda en un JSON en la carpeta de configuracion del usuario. Sirve
para autocompletar el campo «Cliente» del formulario y para elegir
destinatarios en la generacion en lote.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import config


@dataclass
class Cliente:
    nombre: str
    nif: str = ""
    telefono: str = ""
    email: str = ""


def _ruta() -> Path:
    return config.config_dir() / "clientes.json"


def cargar() -> list[Cliente]:
    try:
        datos = json.loads(_ruta().read_text("utf-8"))
    except Exception:
        return []
    return [Cliente(**d) for d in datos]


def guardar(clientes: list[Cliente]) -> None:
    ordenados = sorted(clientes, key=lambda c: c.nombre.lower())
    _ruta().write_text(
        json.dumps([asdict(c) for c in ordenados], ensure_ascii=False, indent=2),
        "utf-8")


def upsert(clientes: list[Cliente], nuevo: Cliente, nombre_original: str = "") -> list[Cliente]:
    """Anade `nuevo`, sustituyendo cualquier cliente con el mismo nombre
    (o con `nombre_original`, si se esta editando y el nombre cambio)."""
    clave_borrar = (nombre_original or nuevo.nombre).strip().lower()
    restantes = [c for c in clientes if c.nombre.strip().lower() != clave_borrar]
    restantes.append(nuevo)
    return restantes


def eliminar(clientes: list[Cliente], nombre: str) -> list[Cliente]:
    clave = nombre.strip().lower()
    return [c for c in clientes if c.nombre.strip().lower() != clave]


def buscar(clientes: list[Cliente], nombre: str) -> Cliente | None:
    clave = nombre.strip().lower()
    for c in clientes:
        if c.nombre.strip().lower() == clave:
            return c
    return None


def asegurar_cliente(nombre: str) -> bool:
    """Si `nombre` no esta ya en la base de datos, lo anade (solo el
    nombre; el resto de campos se pueden completar luego desde «Clientes»).
    Devuelve True si se ha anadido un cliente nuevo."""
    nombre = nombre.strip()
    if not nombre:
        return False
    clientes = cargar()
    if buscar(clientes, nombre):
        return False
    clientes.append(Cliente(nombre=nombre))
    guardar(clientes)
    return True
