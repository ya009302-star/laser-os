"""選択素子のパラメータ編集パネル.

新しい素子型を追加した場合は FIELD_SPECS に編集項目を登録する.
spec: (表示名, 属性名, 単位倍率(GUI→内部), suffix, decimals, min, max)
"""
from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from ..core.elements import FlatMirror, CurvedMirror, ThinLens, Crystal

FIELD_SPECS = {
    FlatMirror: [("入射角", "aoi_deg", 1.0, " °", 1, 0.0, 80.0),
                 ("GDD/反射", "gdd_fs2", 1.0, " fs²", 1, -1e6, 1e6),
                 ("TOD/反射", "tod_fs3", 1.0, " fs³", 1, -1e7, 1e7)],
    CurvedMirror: [("曲率半径 R", "roc", 1e-3, " mm", 1, -1e5, 1e5),
                   ("入射角", "aoi_deg", 1.0, " °", 1, 0.0, 80.0),
                   ("GDD/反射", "gdd_fs2", 1.0, " fs²", 1, -1e6, 1e6),
                   ("TOD/反射", "tod_fs3", 1.0, " fs³", 1, -1e7, 1e7)],
    ThinLens: [("焦点距離 f", "f", 1e-3, " mm", 1, -1e5, 1e5),
               ("GDD/通過", "gdd_fs2", 1.0, " fs²", 1, -1e6, 1e6),
               ("TOD/通過", "tod_fs3", 1.0, " fs³", 1, -1e7, 1e7)],
    Crystal: [("光路長 ℓ", "length", 1e-3, " mm", 2, 0.01, 1000.0),
              ("屈折率 n", "n", 1.0, "", 3, 1.0, 5.0),
              ("熱レンズ f (0=無効)", "thermal_f", 1e-3, " mm", 1, -1e6, 1e6),
              ("追加GDD/通過", "gdd_fs2", 1.0, " fs²", 1, -1e6, 1e6),
              ("追加TOD/通過", "tod_fs3", 1.0, " fs³", 1, -1e7, 1e7)],
}


class Inspector(QtWidgets.QGroupBox):
    """選択中の素子と隣接間隔の編集. 値変更で changed シグナルを発火."""
    changed = QtCore.Signal()

    def __init__(self, parent=None):
        super().__init__("インスペクタ", parent)
        self._cav = None
        self._index = -1
        self._building = False
        self._form = QtWidgets.QFormLayout(self)

    # ---------------------------------------------------------------
    def set_target(self, cav, index: int):
        self._cav, self._index = cav, index
        self._rebuild()

    def _clear(self):
        while self._form.rowCount():
            self._form.removeRow(0)

    def _rebuild(self):
        self._building = True
        self._clear()
        cav, i = self._cav, self._index
        if cav is None or not (0 <= i < len(cav.elements)):
            self._form.addRow(QtWidgets.QLabel("素子を選択してください"))
            self._building = False
            return
        el = cav.elements[i]

        name_edit = QtWidgets.QLineEdit(el.name)
        name_edit.editingFinished.connect(
            lambda e=el, w=name_edit: self._set_attr(e, "name", w.text()))
        self._form.addRow("名前", name_edit)
        self._form.addRow("種類", QtWidgets.QLabel(type(el).__name__))

        for spec in FIELD_SPECS.get(type(el), []):
            label, attr, scale, suffix, dec, lo, hi = spec
            spin = QtWidgets.QDoubleSpinBox(
                suffix=suffix, decimals=dec, minimum=lo, maximum=hi)
            spin.setValue(getattr(el, attr) / scale)
            spin.setKeyboardTracking(False)
            spin.valueChanged.connect(
                lambda v, e=el, a=attr, s=scale: self._set_attr(e, a, v * s))
            self._form.addRow(label, spin)

        if isinstance(el, (FlatMirror, CurvedMirror)) and el.role == "fold":
            combo = QtWidgets.QComboBox()
            combo.addItems(["左折 (+1)", "右折 (-1)"])
            combo.setCurrentIndex(0 if el.turn >= 0 else 1)
            combo.currentIndexChanged.connect(
                lambda k, e=el: self._set_attr(e, "turn", 1 if k == 0 else -1))
            self._form.addRow("折返し方向", combo)
        if isinstance(el, Crystal):
            chk = QtWidgets.QCheckBox()
            chk.setChecked(el.brewster)
            chk.toggled.connect(
                lambda v, e=el: self._set_attr(e, "brewster", bool(v)))
            self._form.addRow("ブリュースター入射", chk)
            combo_t = QtWidgets.QComboBox()
            combo_t.addItems(["+1 (左)", "-1 (右)"])
            combo_t.setCurrentIndex(0 if el.tilt >= 0 else 1)
            combo_t.currentIndexChanged.connect(
                lambda k, e=el: self._set_attr(e, "tilt", 1 if k == 0 else -1))
            self._form.addRow("傾き向き (横変位)", combo_t)
            mat_edit = QtWidgets.QLineEdit(el.material)
            mat_edit.setPlaceholderText("材料DB名 (例: fused_silica, 空=未使用)")
            mat_edit.setToolTip("分散記帳専用. ABCD の屈折率 n は変更しない")
            mat_edit.editingFinished.connect(
                lambda e=el, w=mat_edit: self._set_attr(
                    e, "material", w.text().strip()))
            self._form.addRow("材料 (分散用)", mat_edit)

        # 隣接間隔
        for off, label in ((-1, "前側の間隔"), (0, "後側の間隔")):
            j = i + off
            if 0 <= j < len(cav.spacings):
                spin = QtWidgets.QDoubleSpinBox(
                    suffix=" mm", decimals=2, minimum=0.0, maximum=10000.0)
                spin.setSingleStep(0.5)
                spin.setValue(cav.spacings[j] * 1e3)
                spin.setKeyboardTracking(False)
                spin.valueChanged.connect(
                    lambda v, jj=j: self._set_spacing(jj, v * 1e-3))
                self._form.addRow(label, spin)
        self._building = False

    # ---------------------------------------------------------------
    def _set_attr(self, el, attr, value):
        if self._building:
            return
        setattr(el, attr, value)
        self.changed.emit()

    def _set_spacing(self, j, value):
        if self._building:
            return
        self._cav.spacings[j] = value
        self.changed.emit()

    def refresh_spacings(self):
        """ドラッグなど外部要因で間隔が変わった際に表示を同期."""
        self._rebuild()
