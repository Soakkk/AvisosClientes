@echo off
REM Compila el ejecutable con PyInstaller usando el entorno virtual.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3.11 -m venv .venv
)

call ".venv\Scripts\python.exe" -m pip install --upgrade pip
call ".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller

echo.
echo Compilando...
call ".venv\Scripts\python.exe" -m PyInstaller --noconfirm AvisosEMarin.spec

echo.
echo Listo. El programa esta en:  dist\AvisosEMarin\AvisosEMarin.exe
pause
