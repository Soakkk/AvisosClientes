# Avisos Asesoría E. Marín

Herramienta de escritorio para generar los **avisos a clientes** (solicitud de
documentación, recordatorios de plazos, cierre de ejercicio, Renta…) siempre con
la **misma estética** de la asesoría y exportarlos a **PDF** para guardar y enviar.

El objetivo es tener un único estilo, coherente con el manual de marca (logo,
colores y pie de página fijos), y poder cambiar solo los datos de cada aviso:
periodo, año, fecha límite, nombre del cliente y la lista de documentos.

![logo](assets/EM_logo_horizontal_claro.jpg)

## Características

- Plantillas predefinidas con la redacción real de la oficina:
  - **Solicitud de documentación — Trimestre**
  - **Recordatorio de plazos — Cierre de trimestre**
  - **4.º Trimestre + Resumen Anual (cierre de ejercicio)** (con felicitación navideña opcional)
  - **Renta — Bienes arrendados**
- Periodo y **fecha límite** que se rellenan solos (1T→abril, 2T→julio, 3T→octubre, 4T→enero).
- Lista de documentos editable y notas adicionales.
- **Vista previa en vivo** idéntica al PDF final.
- Cabecera con el logo, colores de marca y pie de página fijo en todos los avisos.

## Estética / manual de estilo

Todo lo que define el estilo está centralizado en [`avisos/config.py`](avisos/config.py):
colores (verde `#2E4A3C`, dorado `#B8995A`), datos del pie de página y tipografía
(EB Garamond, incluida en `assets/fonts`, licencia OFL).

Para cambiar el logo, basta con dejar un archivo cuyo nombre empiece por `EM_logo`
en la carpeta `assets/`. Si pones un **PNG con fondo transparente** se usará ese
en lugar del JPG (queda más limpio sobre el folio blanco).

## Ejecutar en desarrollo

Requiere Python 3.11+.

```bat
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

## Compilar el ejecutable (.exe)

```bat
build_exe.bat
```

Genera `dist\AvisosEMarin\AvisosEMarin.exe` (carpeta autocontenida, igual que el
Escáner de Fotos).

## Crear el instalador

1. Compila el .exe con `build_exe.bat`.
2. Abre `installer\AvisosEMarin.iss` con [Inno Setup](https://jrsoftware.org/isdl.php) y pulsa *Compile*.
3. El instalador queda en `dist_installer\`.

## Estructura

```
AvisosClientes/
├─ avisos/
│  ├─ config.py      # manual de estilo: colores, datos fijos, rutas
│  ├─ templates.py   # plantillas y textos
│  ├─ render.py      # composición y export a PDF / vista previa
│  ├─ app.py         # ventana principal (PySide6)
│  └─ main.py        # arranque
├─ assets/           # logo, icono y fuentes
├─ scripts/smoketest.py
├─ run.py            # lanzador en desarrollo
├─ AvisosEMarin.spec # PyInstaller
└─ installer/        # Inno Setup
```

## Licencia

Código propio de Asesoría E. Marín. Fuente EB Garamond bajo
[SIL Open Font License](assets/fonts/OFL.txt).
