"""下部ドックのプロット類: コースティック w(s) と安定性スキャン."""
from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6 import QtCore, QtWidgets

from ..analysis.scan import scan_spacing

pg.setConfigOptions(antialias=True, background="#14181f", foreground="#d8dee9")

PEN_T = pg.mkPen("#ffbf33", width=2)
PEN_S = pg.mkPen("#59bfff", width=2, style=QtCore.Qt.DashLine)


class CausticPlot(pg.PlotWidget):
    """経路に沿ったビーム半径 w(s) [µm]."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLabel("bottom", "経路 s", units="mm")
        self.setLabel("left", "ビーム半径 w", units="µm")
        self.addLegend(offset=(10, 10))
        self.showGrid(x=True, y=True, alpha=0.25)
        self._curve_t = self.plot([], [], pen=PEN_T, name="接線面 w_t")
        self._curve_s = self.plot([], [], pen=PEN_S, name="サジタル面 w_s")
        self._marks = []

    def update_result(self, cav, res):
        s = res.s_axis * 1e3
        self._curve_t.setData(s, res.w["t"] * 1e6)
        self._curve_s.setData(s, res.w["s"] * 1e6)
        for m in self._marks:
            self.removeItem(m)
        self._marks = []
        for el, pos in zip(cav.elements, res.element_s):
            line = pg.InfiniteLine(pos=pos * 1e3, angle=90,
                                   pen=pg.mkPen("#666c78", width=1),
                                   label=el.name,
                                   labelOpts={"position": 0.92, "color": "#9aa3b2",
                                              "movable": False})
            self.addItem(line)
            self._marks.append(line)


class ScanPanel(QtWidgets.QWidget):
    """間隔を掃引して安定性パラメータ m とモード径を表示する."""

    def __init__(self, get_cavity, parent=None):
        super().__init__(parent)
        self._get_cavity = get_cavity
        form = QtWidgets.QHBoxLayout()
        self.combo_spacing = QtWidgets.QComboBox()
        self.spin_min = QtWidgets.QDoubleSpinBox(
            suffix=" mm", decimals=2, minimum=0, maximum=10000)
        self.spin_max = QtWidgets.QDoubleSpinBox(
            suffix=" mm", decimals=2, minimum=0, maximum=10000)
        self.combo_target = QtWidgets.QComboBox()
        btn = QtWidgets.QPushButton("スキャン実行")
        btn.clicked.connect(self.run_scan)
        for w_, label in ((self.combo_spacing, "間隔"),
                          (self.spin_min, "最小"), (self.spin_max, "最大"),
                          (self.combo_target, "w 評価位置")):
            form.addWidget(QtWidgets.QLabel(label))
            form.addWidget(w_)
        form.addWidget(btn)
        form.addStretch(1)

        glw = pg.GraphicsLayoutWidget()
        self.plot_m = glw.addPlot(row=0, col=0)
        self.plot_m.setLabel("left", "安定性 m")
        self.plot_m.addLegend(offset=(10, 5))
        self.plot_m.showGrid(x=True, y=True, alpha=0.25)
        for y in (-1, 1):
            self.plot_m.addItem(pg.InfiniteLine(
                pos=y, angle=0, pen=pg.mkPen("#aa4444", style=QtCore.Qt.DotLine)))
        self.plot_w = glw.addPlot(row=1, col=0)
        self.plot_w.setLabel("left", "w", units="µm")
        self.plot_w.setLabel("bottom", "間隔", units="mm")
        self.plot_w.showGrid(x=True, y=True, alpha=0.25)
        self.plot_w.setXLink(self.plot_m)
        self._cm_t = self.plot_m.plot([], [], pen=PEN_T, name="m_t")
        self._cm_s = self.plot_m.plot([], [], pen=PEN_S, name="m_s")
        self._cw_t = self.plot_w.plot([], [], pen=PEN_T)
        self._cw_s = self.plot_w.plot([], [], pen=PEN_S)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addLayout(form)
        lay.addWidget(glw, 1)

    def refresh_choices(self):
        cav = self._get_cavity()
        cur_sp = self.combo_spacing.currentIndex()
        cur_tg = self.combo_target.currentIndex()
        self.combo_spacing.clear()
        for i in range(len(cav.spacings)):
            a, b = cav.elements[i].name, cav.elements[i + 1].name
            self.combo_spacing.addItem(f"d{i}: {a} – {b}")
        self.combo_target.clear()
        self.combo_target.addItem("最小ウエスト")
        for i, el in enumerate(cav.elements):
            self.combo_target.addItem(f"{el.name} 上")
        if 0 <= cur_sp < self.combo_spacing.count():
            self.combo_spacing.setCurrentIndex(cur_sp)
        if 0 <= cur_tg < self.combo_target.count():
            self.combo_target.setCurrentIndex(cur_tg)

    def run_scan(self):
        cav = self._get_cavity()
        idx = self.combo_spacing.currentIndex()
        if idx < 0 or idx >= len(cav.spacings):
            return
        lo, hi = self.spin_min.value() * 1e-3, self.spin_max.value() * 1e-3
        if hi <= lo:
            center = cav.spacings[idx]
            lo, hi = max(0.0, center * 0.5), center * 1.5
            self.spin_min.setValue(lo * 1e3)
            self.spin_max.setValue(hi * 1e3)
        target = self.combo_target.currentIndex() - 1
        out = scan_spacing(cav, idx, np.linspace(lo, hi, 400),
                           target_element=target if target >= 0 else None)
        v = out["values"] * 1e3
        self._cm_t.setData(v, out["m_t"])
        self._cm_s.setData(v, out["m_s"])
        self._cw_t.setData(v, out["w_t"] * 1e6)
        self._cw_s.setData(v, out["w_s"] * 1e6)
        self.plot_m.setYRange(-2.5, 2.5)
