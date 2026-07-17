"""Controles que no cambian de valor accidentalmente con la rueda.

Al ignorar el evento, Qt puede entregarlo al panel desplazable padre: la
rueda sigue moviendo la pantalla, pero nunca cambia una fecha, un año o una
opción mientras el usuario simplemente está recorriendo el formulario.
"""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDateEdit, QDoubleSpinBox, QFontComboBox, QSpinBox


class _SinCambioPorRueda:
    def wheelEvent(self, event) -> None:  # noqa: N802
        event.ignore()


class ComboSinRueda(_SinCambioPorRueda, QComboBox):
    pass


class FechaSinRueda(_SinCambioPorRueda, QDateEdit):
    pass


class SpinSinRueda(_SinCambioPorRueda, QSpinBox):
    pass


class DoubleSpinSinRueda(_SinCambioPorRueda, QDoubleSpinBox):
    pass


class FuenteSinRueda(_SinCambioPorRueda, QFontComboBox):
    pass
