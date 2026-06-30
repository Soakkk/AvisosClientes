import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from datetime import date
from PySide6.QtWidgets import QApplication
from avisos import templates as T
from avisos.render import render_pdf, render_preview

app = QApplication([])
for p in T.PLANTILLAS:
    ctx = T.Contexto(periodo="4T" if p.id == "cierre_anual" else "1T",
                     anio=2026, cliente="Juan Pérez García",
                     navidad=p.usa_navidad,
                     documentos=p.documentos_def)
    out = f"_test_{p.id}.pdf"
    render_pdf(ctx, p, out)
    img = render_preview(ctx, p, dpi=120)
    img.save(f"_test_{p.id}.png")
    print(p.id, "->", out, os.path.getsize(out), "bytes; png", img.width(), "x", img.height())
print("OK")
