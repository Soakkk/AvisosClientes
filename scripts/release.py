"""Prepara una version nueva de principio a fin.

Uso (desde la raiz del proyecto):
    .venv\\Scripts\\python scripts\\release.py 1.7.0

Hace, en orden:
  1. Actualiza la version en avisos/__init__.py y installer/AvisosEMarin.iss
  2. Ejecuta la bateria de pruebas (scripts/test_full.py) y se detiene si falla
  3. Compila el ejecutable con PyInstaller
  4. Compila el instalador con Inno Setup
  5. Crea el zip portable

No toca git ni GitHub: el commit, push y release se hacen aparte.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ISCC = Path(r"C:\Users\ASESORIA\AppData\Local\Programs\Inno Setup 6\ISCC.exe")


def paso(titulo: str) -> None:
    print(f"\n=== {titulo} ===", flush=True)


def actualizar_version(version: str) -> None:
    paso(f"1/5 Actualizando version a {version}")
    init = RAIZ / "avisos" / "__init__.py"
    init.write_text(re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"',
                           init.read_text("utf-8")), "utf-8")
    iss = RAIZ / "installer" / "AvisosEMarin.iss"
    iss.write_text(re.sub(r'#define MyAppVersion "[^"]+"',
                          f'#define MyAppVersion "{version}"',
                          iss.read_text("utf-8")), "utf-8")
    print("  avisos/__init__.py e installer/AvisosEMarin.iss actualizados")


def ejecutar_tests() -> None:
    paso("2/5 Ejecutando pruebas")
    tmp = RAIZ / "_test_release_tmp.py"
    shutil.copy(RAIZ / "scripts" / "test_full.py", tmp)
    try:
        r = subprocess.run([sys.executable, str(tmp)], cwd=RAIZ)
        if r.returncode != 0:
            sys.exit("PRUEBAS FALLIDAS - release cancelada")
    finally:
        tmp.unlink(missing_ok=True)


def compilar_exe() -> None:
    paso("3/5 Compilando ejecutable (PyInstaller)")
    # Cerrar la app si esta abierta (bloquearia los archivos de dist/)
    subprocess.run(["taskkill", "/IM", "AvisosEMarin.exe", "/F"], capture_output=True)
    r = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm",
                        "AvisosEMarin.spec"], cwd=RAIZ)
    if r.returncode != 0:
        sys.exit("PyInstaller fallo")


def compilar_instalador() -> None:
    paso("4/5 Compilando instalador (Inno Setup)")
    r = subprocess.run([str(ISCC), str(RAIZ / "installer" / "AvisosEMarin.iss")])
    if r.returncode != 0:
        sys.exit("Inno Setup fallo")


def crear_zip(version: str) -> Path:
    paso("5/5 Creando zip portable")
    destino = RAIZ / f"AvisosEMarin_v{version}.zip"
    origen = RAIZ / "dist" / "AvisosEMarin"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for archivo in origen.rglob("*"):
            z.write(archivo, archivo.relative_to(origen))
    print(f"  {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
    return destino


def main() -> None:
    if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        sys.exit("Uso: python scripts/release.py <version>   (p. ej. 1.7.0)")
    version = sys.argv[1]
    actualizar_version(version)
    ejecutar_tests()
    compilar_exe()
    compilar_instalador()
    crear_zip(version)
    print(f"\nLISTO. Artefactos de la v{version}:")
    print(f"  dist_installer/AvisosEMarin_Setup_{version}.exe")
    print(f"  AvisosEMarin_v{version}.zip")
    print("Falta: commit + push + gh release create")


if __name__ == "__main__":
    main()
