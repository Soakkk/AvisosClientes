"""Comprobacion de actualizaciones contra los releases de GitHub.

Usa solo la biblioteca estandar (urllib) para no anadir dependencias.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import config

_TIMEOUT = 6


@dataclass
class VersionRemota:
    tag: str
    version: tuple[int, int, int]
    url_instalador: str
    url_sha256: str
    notas: str


def _version_tupla(texto: str) -> tuple[int, int, int]:
    numeros = re.findall(r"\d+", texto)
    partes = [int(n) for n in numeros[:3]]
    while len(partes) < 3:
        partes.append(0)
    return (partes[0], partes[1], partes[2])


def comprobar() -> VersionRemota | None:
    """Consulta la ultima release en GitHub. None si falla o no hay instalador."""
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
    peticion = urllib.request.Request(
        url, headers={"User-Agent": "AvisosEMarin", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(peticion, timeout=_TIMEOUT) as resp:
            datos = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    tag = datos.get("tag_name", "")
    instalador = ""
    sha256 = ""
    for asset in datos.get("assets", []):
        nombre = asset.get("name", "")
        if nombre.lower().endswith(".exe") and "setup" in nombre.lower():
            instalador = asset.get("browser_download_url", "")
        elif nombre.lower().endswith(".sha256"):
            sha256 = asset.get("browser_download_url", "")
    if not tag or not instalador:
        return None
    return VersionRemota(
        tag=tag, version=_version_tupla(tag),
        url_instalador=instalador, url_sha256=sha256,
        notas=datos.get("body", ""))


def hay_actualizacion(version_actual: str, remota: VersionRemota) -> bool:
    return remota.version > _version_tupla(version_actual)
