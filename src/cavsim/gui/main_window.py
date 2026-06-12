"""メインウィンドウ: 3D ビュー / 素子リスト / インスペクタ / プロットの統合."""
from __future__ import annotations

import copy

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from .. import presets
from ..core import geometry
from ..core.cavity import Cavity
from ..core.elements import FlatMirror, CurvedMirror, ThinLens, Crystal
from ..io import project
from .inspector import Inspector
from .plots import CausticPlot, Map2DPanel, ScanPanel
from .viewport3d import Viewport3D

MIN_GAP = 0.5e-3  # ドラッグ時に許す最小間隔 [m]


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("cavsim — レーザー共振器シミュレータ")
        self.resize(1400, 860)
        self.cavity: Cavity = presets.zfold_ybyag()
        self.current_path: str | None = None
        self.selected = -1
        self._build_ui()
        self._build_menu()
        self.recompute(full=True)

    # ---------------------------------------------------------------
    def _build_ui(self):
        self.viewport = Viewport3D()
        self.viewport.elementClicked.connect(self.select_element)
        self.viewport.elementDragged.connect(self.on_drag)

        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.currentRowChanged.connect(self.select_element)
        self.inspector = Inspector()
        self.inspector.changed.connect(lambda: self.recompute())

        self.wl_spin = QtWidgets.QDoubleSpinBox(
            suffix=" nm", decimals=1, minimum=100, maximum=20000)
        self.wl_spin.setValue(self.cavity.wavelength * 1e9)
        self.wl_spin.setKeyboardTracking(False)
        self.wl_spin.valueChanged.connect(self._on_wavelength)

        self.scale_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.scale_slider.setRange(0, 100)        # 10^(1..4) を対数で
        self.scale_slider.setValue(55)
        self.scale_slider.valueChanged.connect(lambda *_: self.refresh_view())
        self.scale_label = QtWidgets.QLabel()

        left = QtWidgets.QWidget()
        ll = QtWidgets.QVBoxLayout(left)
        form_top = QtWidgets.QFormLayout()
        form_top.addRow("波長", self.wl_spin)
        ll.addLayout(form_top)
        ll.addWidget(QtWidgets.QLabel("素子リスト"))
        ll.addWidget(self.list_widget, 1)
        ll.addWidget(self.inspector, 0)
        srow = QtWidgets.QHBoxLayout()
        srow.addWidget(QtWidgets.QLabel("ビーム表示倍率"))
        srow.addWidget(self.scale_slider, 1)
        srow.addWidget(self.scale_label)
        ll.addLayout(srow)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(self.viewport)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([330, 1000])
        self.setCentralWidget(splitter)

        self.caustic_plot = CausticPlot()
        self.scan_panel = ScanPanel(lambda: self.cavity)
        self.map2d_panel = Map2DPanel(lambda: self.cavity, self._apply_two_spacings)
        tabs = QtWidgets.QTabWidget()
        tabs.addTab(self.caustic_plot, "コースティック w(s)")
        tabs.addTab(self.scan_panel, "安定性スキャン")
        tabs.addTab(self.map2d_panel, "2Dマップ")
        dock = QtWidgets.QDockWidget("解析", self)
        dock.setWidget(tabs)
        dock.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, dock)
        dock.setMinimumHeight(230)

        self.status = self.statusBar()

    def _build_menu(self):
        m_file = self.menuBar().addMenu("ファイル(&F)")
        for label, slot, key in (
                ("開く...", self.open_file, "Ctrl+O"),
                ("保存", self.save_file, "Ctrl+S"),
                ("名前を付けて保存...", self.save_file_as, "Ctrl+Shift+S")):
            act = QtGui.QAction(label, self)
            act.setShortcut(key)
            act.triggered.connect(slot)
            m_file.addAction(act)

        m_preset = self.menuBar().addMenu("プリセット(&P)")
        for name, fn in presets.PRESETS.items():
            act = QtGui.QAction(name, self)
            act.triggered.connect(lambda *_, f=fn: self.load_cavity(f()))
            m_preset.addAction(act)

        m_edit = self.menuBar().addMenu("素子(&E)")
        adders = (
            ("凹面折返しミラーを追加", lambda: CurvedMirror(
                name="CM", roc=0.1, aoi_deg=8.0, turn=1, role="fold")),
            ("平面折返しミラーを追加", lambda: FlatMirror(
                name="FM", aoi_deg=22.5, turn=1, role="fold")),
            ("薄肉レンズを追加", lambda: ThinLens(name="L", f=0.1)),
            ("結晶/板を追加", lambda: Crystal(
                name="X", length=3e-3, n=1.82, brewster=True)),
        )
        for label, factory in adders:
            act = QtGui.QAction(label, self)
            act.triggered.connect(lambda *_, f=factory: self.add_element(f()))
            m_edit.addAction(act)
        m_edit.addSeparator()
        act_del = QtGui.QAction("選択素子を削除", self)
        act_del.setShortcut(QtGui.QKeySequence.Delete)
        act_del.triggered.connect(self.delete_element)
        m_edit.addAction(act_del)

        m_ana = self.menuBar().addMenu("解析(&A)")
        act_comp = QtGui.QAction("非点収差補償角を計算...", self)
        act_comp.triggered.connect(self.compute_compensation_angle)
        m_ana.addAction(act_comp)
        act_disp = QtGui.QAction("往復分散レポート (GDD/TOD)...", self)
        act_disp.triggered.connect(self.show_dispersion_report)
        m_ana.addAction(act_disp)
        act_sens = QtGui.QAction("ミラー傾き感度...", self)
        act_sens.triggered.connect(self.show_sensitivity_report)
        m_ana.addAction(act_sens)
        act_marg = QtGui.QAction("安定許容差 (各間隔)...", self)
        act_marg.triggered.connect(self.show_margins_report)
        m_ana.addAction(act_marg)
        act_out = QtGui.QAction("出力ビーム (端面鏡の外側)...", self)
        act_out.triggered.connect(self.show_output_beam_report)
        m_ana.addAction(act_out)

    # --- 解析アクション ----------------------------------------------
    def compute_compensation_angle(self):
        """折返し凹面鏡の補償角を閉形式+数値最適化で求め, 適用を提案する."""
        from ..analysis.astigmatism import (compensation_angle,
                                            find_compensation_angle)
        folds = [el for el in self.cavity.elements
                 if isinstance(el, CurvedMirror) and el.role == "fold"]
        crystals = [el for el in self.cavity.elements
                    if isinstance(el, Crystal) and el.brewster]
        if not folds or not crystals:
            QtWidgets.QMessageBox.information(
                self, "補償角",
                "折返し凹面鏡とブリュースター結晶の両方が必要です")
            return
        cr = crystals[0]
        th_cf = np.degrees(compensation_angle(
            folds[0].roc, cr.length, cr.n, n_mirrors=len(folds)))
        try:
            res = find_compensation_angle(self.cavity, metric="match_m")
            numeric = f"{res.theta_deg:.2f}° (|m_t−m_s|={res.metric_value:.2e})"
        except Exception as exc:                       # noqa: BLE001
            res, numeric = None, f"失敗: {exc}"
        msg = (f"閉形式 (第一次近似): {th_cf:.2f}°\n"
               f"数値最適化 (厳密行列): {numeric}\n\n"
               f"数値解を折返し凹面鏡 {len(folds)} 枚の入射角に適用しますか?")
        btn = QtWidgets.QMessageBox.question(self, "非点収差補償角", msg)
        if btn == QtWidgets.QMessageBox.Yes and res is not None:
            for el in folds:
                el.aoi_deg = res.theta_deg
            self.recompute(full=True)

    def _apply_two_spacings(self, ia, va, ib, vb):
        """2D マップのクリックから両間隔を設定する."""
        self.cavity.spacings[ia] = max(MIN_GAP, float(va))
        self.cavity.spacings[ib] = max(MIN_GAP, float(vb))
        self.recompute(light=True)
        self.status.showMessage(
            f"d{ia} = {va*1e3:.2f} mm, d{ib} = {vb*1e3:.2f} mm に設定", 4000)

    def _show_text_dialog(self, title: str, text: str, note: str = ""):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(title)
        lay = QtWidgets.QVBoxLayout(dlg)
        box = QtWidgets.QPlainTextEdit(text)
        box.setReadOnly(True)
        box.setFont(QtGui.QFont("monospace"))
        box.setMinimumSize(680, 300)
        lay.addWidget(box)
        if note:
            lab = QtWidgets.QLabel(note)
            lab.setWordWrap(True)
            lay.addWidget(lab)
        dlg.exec()

    def show_sensitivity_report(self):
        from ..analysis.sensitivity import sensitivity_text
        try:
            txt = sensitivity_text(self.cavity)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "傾き感度", str(exc))
            return
        self._show_text_dialog(
            "ミラー傾き感度", txt,
            "符号は規約上のもの (PHYSICS.md §12)。大きさで感度を比較してください。"
            " 折返し鏡は1往復2反射として扱う第一次近似です。")

    def show_margins_report(self):
        from ..analysis.scan import stability_margins
        try:
            margins = stability_margins(self.cavity)
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "安定許容差", str(exc))
            return
        fmt = lambda v: "範囲内に境界なし" if v is None else f"{v*1e3:8.3f} mm"
        lines = ["各間隔を単独で動かした場合の不安定化までの距離", ""]
        for k, (down, up) in enumerate(margins):
            a, b = self.cavity.elements[k].name, self.cavity.elements[k+1].name
            lines.append(f"d{k} ({a} – {b}, 現在 "
                         f"{self.cavity.spacings[k]*1e3:.2f} mm): "
                         f"−{fmt(down)} / +{fmt(up)}")
        self._show_text_dialog("安定許容差", "\n".join(lines),
                               "探索範囲は現在値 ±50%。他の間隔は固定。")

    def show_output_beam_report(self):
        from ..analysis.beamfit import output_beam_text
        from ..core.elements import FlatMirror
        texts = []
        for idx in (len(self.cavity.elements) - 1, 0):
            if isinstance(self.cavity.elements[idx], FlatMirror):
                try:
                    texts.append(output_beam_text(self.cavity, idx))
                except ValueError as exc:
                    texts.append(f"({self.cavity.elements[idx].name}: {exc})")
        if not texts:
            QtWidgets.QMessageBox.information(
                self, "出力ビーム", "平面の端面鏡がありません (曲面端は未対応)")
            return
        self._show_text_dialog("出力ビーム", "\n\n".join(texts),
                               "基板の屈折・レンズ効果は無視 (薄い平面 OC 近似)。")

    def show_dispersion_report(self):
        from ..analysis.dispersion import round_trip_dispersion
        try:
            rep = round_trip_dispersion(self.cavity)
        except KeyError as exc:
            QtWidgets.QMessageBox.warning(self, "分散レポート", str(exc))
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("往復分散レポート")
        lay = QtWidgets.QVBoxLayout(dlg)
        txt = QtWidgets.QPlainTextEdit(rep.to_text())
        txt.setReadOnly(True)
        txt.setFont(QtGui.QFont("monospace"))
        txt.setMinimumSize(640, 280)
        lay.addWidget(txt)
        note = QtWidgets.QLabel(
            "ミラー/レンズの GDD・TOD はインスペクタでユーザー入力 "
            "(データシート値)。結晶は材料DB (出典付き) + 追加分。")
        note.setWordWrap(True)
        lay.addWidget(note)
        dlg.exec()

    # ---------------------------------------------------------------
    def _w_scale(self) -> float:
        return 10 ** (1.0 + 3.0 * self.scale_slider.value() / 100.0)

    def _on_wavelength(self, v):
        self.cavity.wavelength = v * 1e-9
        self.recompute()

    def select_element(self, idx: int):
        if idx == self.selected:
            return
        self.selected = idx
        if self.list_widget.currentRow() != idx:
            self.list_widget.blockSignals(True)
            self.list_widget.setCurrentRow(idx)
            self.list_widget.blockSignals(False)
        self.inspector.set_target(self.cavity, idx)
        self.refresh_view()

    def on_drag(self, idx: int, delta: float, after: bool):
        j = idx if after else idx - 1
        # 体積素子(結晶)の後側間隔は素子インデックスと一致しないため補正不要(線形リスト)
        if not (0 <= j < len(self.cavity.spacings)):
            return
        self.cavity.spacings[j] = max(MIN_GAP, self.cavity.spacings[j] + delta)
        self.recompute(light=True)

    def add_element(self, el):
        i = self.selected if 0 <= self.selected < len(self.cavity.elements) - 1 \
            else len(self.cavity.elements) - 2
        d = self.cavity.spacings[i]
        self.cavity.elements.insert(i + 1, el)
        self.cavity.spacings[i] = d / 2
        self.cavity.spacings.insert(i + 1, d / 2)
        self.recompute(full=True)
        self.select_element(i + 1)

    def delete_element(self):
        i = self.selected
        if not (1 <= i <= len(self.cavity.elements) - 2):
            self.status.showMessage("端面鏡は削除できません", 4000)
            return
        d = self.cavity.spacings[i - 1] + self.cavity.spacings[i]
        del self.cavity.elements[i]
        del self.cavity.spacings[i]
        self.cavity.spacings[i - 1] = d
        self.selected = -1
        self.recompute(full=True)

    # ---------------------------------------------------------------
    def recompute(self, full: bool = False, light: bool = False):
        errs = self.cavity.validate()
        if errs:
            self.status.showMessage("⚠ " + " / ".join(errs))
            return
        try:
            self.result = self.cavity.compute(max_step=2e-3)
        except Exception as exc:                       # noqa: BLE001
            self.status.showMessage(f"計算エラー: {exc}")
            return
        if full:
            self._refresh_list()
            self.scan_panel.refresh_choices()
            self.map2d_panel.refresh_choices()
            self.inspector.set_target(self.cavity, self.selected)
        if light:
            self.inspector.refresh_spacings()
        self.refresh_view()
        self.caustic_plot.update_result(self.cavity, self.result)
        self._update_status()

    def _refresh_list(self):
        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for i, el in enumerate(self.cavity.elements):
            tag = "端面" if el.is_end else ("折返" if el.deflects else "透過")
            self.list_widget.addItem(f"{i}: {el.name}  [{tag}]")
        self.list_widget.setCurrentRow(self.selected)
        self.list_widget.blockSignals(False)

    def refresh_view(self):
        if not hasattr(self, "result"):
            return
        scale = self._w_scale()
        self.scale_label.setText(f"×{scale:,.0f}")
        poses, _ = geometry.build_layout(self.cavity)
        pts = geometry.caustic_points(self.cavity, self.result, w_scale=scale)
        self.viewport.set_scene(poses, pts, self.selected)

    def _update_status(self):
        r = self.result
        parts = [f"安定性: m_t={r.m['t']:+.3f} m_s={r.m['s']:+.3f}"]
        if not (r.stable["t"] and r.stable["s"]):
            parts.append("【不安定】")
        cr = next((i for i, el in enumerate(self.cavity.elements)
                   if isinstance(el, Crystal)), None)
        if cr is not None and r.stable["t"] and r.stable["s"]:
            wt, ws = r.element_w[cr]
            parts.append(f"{self.cavity.elements[cr].name} 内 "
                         f"w_t={wt*1e6:.1f}µm w_s={ws*1e6:.1f}µm")
        parts.append(f"全長 {r.total_length*1e3:.1f} mm")
        self.status.showMessage("   |   ".join(parts))

    # ---------------------------------------------------------------
    def load_cavity(self, cav: Cavity, path: str | None = None):
        self.cavity = cav
        self.current_path = path
        self.selected = -1
        self.wl_spin.blockSignals(True)
        self.wl_spin.setValue(cav.wavelength * 1e9)
        self.wl_spin.blockSignals(False)
        self.setWindowTitle(f"cavsim — {cav.name}")
        self.recompute(full=True)

    def open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "共振器を開く", "", "Cavity JSON (*.json)")
        if not path:
            return
        try:
            self.load_cavity(project.load(path), path)
        except Exception as exc:                       # noqa: BLE001
            QtWidgets.QMessageBox.warning(self, "読込エラー", str(exc))

    def save_file(self):
        if not self.current_path:
            return self.save_file_as()
        project.save(self.cavity, self.current_path)
        self.status.showMessage(f"保存しました: {self.current_path}", 4000)

    def save_file_as(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "名前を付けて保存", f"{self.cavity.name}.json",
            "Cavity JSON (*.json)")
        if not path:
            return
        self.current_path = path
        self.save_file()
