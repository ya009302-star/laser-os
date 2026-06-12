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


class Map2DPanel(QtWidgets.QWidget):
    """間隔 2 つの同時掃引による 2D 安定領域マップ.

    クリックで両間隔をその点に設定できる (apply_cb で MainWindow に反映)。
    """

    def __init__(self, get_cavity, apply_cb, parent=None):
        super().__init__(parent)
        self._get_cavity = get_cavity
        self._apply_cb = apply_cb
        self._extent = None                    # (a0, a1, b0, b1) [m]

        form = QtWidgets.QHBoxLayout()
        self.combo_a = QtWidgets.QComboBox()
        self.combo_b = QtWidgets.QComboBox()
        self.spin_span = QtWidgets.QDoubleSpinBox(
            suffix=" %", decimals=0, minimum=5, maximum=90)
        self.spin_span.setValue(30)
        btn = QtWidgets.QPushButton("マップ計算")
        btn.clicked.connect(self.run_map)
        for w_, label in ((self.combo_a, "縦軸の間隔"),
                          (self.combo_b, "横軸の間隔"),
                          (self.spin_span, "範囲 ±")):
            form.addWidget(QtWidgets.QLabel(label))
            form.addWidget(w_)
        form.addWidget(btn)
        self.info = QtWidgets.QLabel("クリックで間隔を設定")
        form.addWidget(self.info)
        form.addStretch(1)

        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "横軸間隔", units="mm")
        self.plot.setLabel("left", "縦軸間隔", units="mm")
        self.img = pg.ImageItem()
        cmap = pg.ColorMap([0.0, 0.999, 1.0],
                           [(40, 44, 52), (40, 44, 52), (70, 190, 120)])
        self.img.setLookupTable(cmap.getLookupTable(nPts=256))
        self.plot.addItem(self.img)
        self._cross_v = pg.InfiniteLine(angle=90,
                                        pen=pg.mkPen("#ffbf33", width=1))
        self._cross_h = pg.InfiniteLine(angle=0,
                                        pen=pg.mkPen("#ffbf33", width=1))
        self.plot.addItem(self._cross_v)
        self.plot.addItem(self._cross_h)
        self.plot.scene().sigMouseClicked.connect(self._on_click)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.addLayout(form)
        lay.addWidget(self.plot, 1)

    def refresh_choices(self):
        cav = self._get_cavity()
        keep_a, keep_b = self.combo_a.currentIndex(), self.combo_b.currentIndex()
        for combo in (self.combo_a, self.combo_b):
            combo.clear()
            for i in range(len(cav.spacings)):
                a, b = cav.elements[i].name, cav.elements[i + 1].name
                combo.addItem(f"d{i}: {a} – {b}")
        if 0 <= keep_a < self.combo_a.count():
            self.combo_a.setCurrentIndex(keep_a)
        if 0 <= keep_b < self.combo_b.count():
            self.combo_b.setCurrentIndex(keep_b)
        elif self.combo_b.count() > 1:
            self.combo_b.setCurrentIndex(min(1, self.combo_b.count() - 1)
                                         if keep_a == 0 else 0)

    def run_map(self, n_grid: int = 101):
        from ..analysis.scan import scan_spacing_2d
        cav = self._get_cavity()
        ia, ib = self.combo_a.currentIndex(), self.combo_b.currentIndex()
        if ia < 0 or ib < 0 or ia == ib:
            self.info.setText("異なる間隔を 2 つ選んでください")
            return
        self._ia, self._ib = ia, ib
        frac = self.spin_span.value() / 100.0
        da, db = cav.spacings[ia], cav.spacings[ib]
        va = np.linspace(max(1e-4, da * (1 - frac)), da * (1 + frac), n_grid)
        vb = np.linspace(max(1e-4, db * (1 - frac)), db * (1 + frac), n_grid)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            out = scan_spacing_2d(cav, ia, ib, va, vb)
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        # ImageItem: 第1軸が x → (b, a) で渡し x=横軸間隔, y=縦軸間隔
        self.img.setImage(out["stable"].T.astype(float), levels=(0.0, 1.0))
        a0, a1 = va[0] * 1e3, va[-1] * 1e3
        b0, b1 = vb[0] * 1e3, vb[-1] * 1e3
        self.img.setRect(QtCore.QRectF(b0, a0, b1 - b0, a1 - a0))
        self._extent = (a0, a1, b0, b1)
        self._update_cross()
        self.info.setText("緑 = 両面安定。クリックで間隔を設定")

    def _update_cross(self):
        cav = self._get_cavity()
        if hasattr(self, "_ia"):
            self._cross_h.setPos(cav.spacings[self._ia] * 1e3)
            self._cross_v.setPos(cav.spacings[self._ib] * 1e3)

    def _on_click(self, ev):
        if self._extent is None or not hasattr(self, "_ia"):
            return
        vb_view = self.plot.getPlotItem().vb
        p = vb_view.mapSceneToView(ev.scenePos())
        x, y = p.x(), p.y()
        a0, a1, b0, b1 = self._extent
        if not (b0 <= x <= b1 and a0 <= y <= a1):
            return
        self._apply_cb(self._ia, y * 1e-3, self._ib, x * 1e-3)
        self._update_cross()
