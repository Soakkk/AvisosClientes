import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from avisos.app import MainWindow

app = QApplication([])
win = MainWindow()
win.resize(1360, 880)
win.show()

def snap(nombre, w, h):
    win.resize(w, h)
    app.processEvents()
    win._resize_timer.stop()
    win._actualizar_preview()
    app.processEvents()
    pix = win.preview.pixmap()
    print(nombre, w, "x", h, "-> preview px:", pix.width(), "x", pix.height())
    pix.save(nombre)

QTimer.singleShot(200, lambda: (
    snap("_prev_1360.png", 1360, 880),
    snap("_prev_1000.png", 1000, 750),
    snap("_prev_maximized.png", 1920, 1040),
    app.quit(),
))
app.exec()
