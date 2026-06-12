"""プリセット共振器. GUI のメニューおよびサンプルとして使用."""
from __future__ import annotations

from .core.cavity import Cavity
from .core.elements import FlatMirror, CurvedMirror, Crystal


def simple_linear() -> Cavity:
    """平面鏡 + 凹面鏡の基本共振器."""
    return Cavity(
        [FlatMirror(name="HR", role="end"),
         CurvedMirror(name="OC", roc=0.5, aoi_deg=0.0, role="end")],
        [0.30], wavelength=1064e-9, name="シンプル線形共振器")


def zfold_ybyag() -> Cavity:
    """Z-fold Yb:YAG フェムト秒発振器の例.

    SESAM -250mm- CM1(R=100mm, 8°) -50.55mm- Yb:YAG(3mm, Brewster)
    -50.55mm- CM2(R=100mm, 8°) -600mm- OC
    結晶内ウエスト ~29×27 µm (t×s).
    """
    return Cavity(
        [FlatMirror(name="SESAM", role="end"),
         CurvedMirror(name="CM1", roc=0.100, aoi_deg=8.0, turn=1, role="fold"),
         Crystal(name="Yb:YAG", length=3e-3, n=1.82, brewster=True),
         CurvedMirror(name="CM2", roc=0.100, aoi_deg=8.0, turn=-1, role="fold"),
         FlatMirror(name="OC", role="end")],
        [0.250, 0.05055, 0.05055, 0.600],
        wavelength=1030e-9, name="Z-fold Yb:YAG")


PRESETS = {
    "Z-fold Yb:YAG (SESAM)": zfold_ybyag,
    "シンプル線形共振器": simple_linear,
}
