import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import tempfile
from pathlib import Path

# Aislar la config del usuario real durante el test
tmp_cfg = Path(tempfile.mkdtemp())
os.environ["APPDATA"] = str(tmp_cfg)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication([])

from avisos import clients as C
from avisos import history as H
from avisos import templates as T
from avisos.app import MainWindow
from avisos.ui.clientes import ClientesDialog, EditorClienteDialog
from avisos.ui.historial import HistorialDialog
from avisos.ui.lote import LoteDialog
from avisos.ui.plantillas import PlantillaEditorDialog

errores = []

def check(nombre, cond):
    estado = "OK " if cond else "FALLO"
    print(f"[{estado}] {nombre}")
    if not cond:
        errores.append(nombre)

# --- clientes ---
clientes = C.cargar()
check("clientes vacio al inicio", clientes == [])
clientes = C.upsert(clientes, C.Cliente(nombre="Juan Pérez García", nif="12345678A", telefono="600111222", email="juan@example.com"))
clientes = C.upsert(clientes, C.Cliente(nombre="Ana López"))
C.guardar(clientes)
clientes2 = C.cargar()
check("clientes se guardan y recargan (2)", len(clientes2) == 2)
check("buscar cliente por nombre", C.buscar(clientes2, "juan pérez garcía") is not None)

# --- historial ---
H.registrar("Solicitud de documentación — Trimestre", "1T", 2026, "Juan Pérez García", r"C:\tmp\aviso.pdf")
hist = H.cargar()
check("historial registra entradas", len(hist) == 1)

# --- overrides de plantillas ---
p = T.PLANTILLAS[0]
check("sin override al inicio", not T.tiene_override(p.id))
T.guardar_override(p.id, "TITULO PERSONALIZADO {anio}", "Estimado/a {cliente}:\n\nTexto de prueba *importante*.")
check("override guardado", T.tiene_override(p.id))
ctx_prueba = T.Contexto(periodo="1T", anio=2026, cliente="Juan Pérez García")
titulo = T.render_titulo(ctx_prueba, p)
check("override se usa en render_titulo", titulo == "TITULO PERSONALIZADO 2026")
cuerpo = T.render_cuerpo(ctx_prueba, p)
check("negrita en override", "<b>importante</b>" in cuerpo)
T.restablecer_override(p.id)
check("restablecer quita el override", not T.tiene_override(p.id))
check("tras restablecer, vuelve al texto de fabrica", T.render_titulo(ctx_prueba, p) != "TITULO PERSONALIZADO 2026")

# --- aviso de fecha ---
import datetime
check("sabado detectado", T.aviso_fecha(datetime.date(2026, 4, 18)) != "")  # 18 abril 2026 es sabado
check("martes no genera aviso (no es finde ni festivo fijo)", T.aviso_fecha(datetime.date(2026, 4, 21)) == "")

# --- render con nif automatico ---
valores = T._valores_comunes(T.Contexto(cliente="Juan Pérez García"))
check("nif se autocompleta desde la base de clientes", valores["nif"] == "12345678A")

# --- MainWindow arranca sin errores ---
win = MainWindow()
win.resize(1360, 880)
win.show()
app.processEvents()
check("MainWindow crea preview", win.preview.label.pixmap() is not None)

# --- dialogos se instancian sin fallar ---
dlg_clientes = ClientesDialog(win)
check("ClientesDialog se construye", dlg_clientes.tabla.rowCount() == 2)
dlg_clientes.close()

dlg_hist = HistorialDialog(win)
check("HistorialDialog se construye", dlg_hist.tabla.rowCount() == 1)
dlg_hist.close()

dlg_editor = PlantillaEditorDialog(win)
app.processEvents()
check("PlantillaEditorDialog previsualiza", dlg_editor.preview.label.pixmap() is not None)
dlg_editor.close()

carpeta_lote = tempfile.mkdtemp()
dlg_lote = LoteDialog(win, win._contexto(), win._plantilla_actual(), carpeta_lote)
from PySide6.QtCore import Qt as QtC
for i in range(dlg_lote.lista.count()):
    dlg_lote.lista.item(i).setCheckState(QtC.Checked)
dlg_lote._carpeta = carpeta_lote
nombres = dlg_lote._nombres_elegidos()
check("lote detecta los 2 clientes marcados", len(nombres) == 2)

# Generar directamente sin pasar por QMessageBox (llamamos a la logica manualmente)
from dataclasses import replace
from avisos.render import render_pdf as _render_pdf
from avisos.util import nombre_archivo as _nombre_archivo
generados = 0
for nombre in nombres:
    ctx = replace(win._contexto(), cliente=nombre)
    ruta = Path(carpeta_lote) / _nombre_archivo(win._plantilla_actual(), ctx)
    _render_pdf(ctx, win._plantilla_actual(), ruta)
    if ruta.exists():
        generados += 1
check("lote genera un PDF por cliente", generados == 2)

if errores:
    print(f"\n{len(errores)} FALLO(S): {errores}")
    sys.exit(1)
print("\nTODO OK")
