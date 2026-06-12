"""熱レンズ (単純モデル) の検証.

thermal_f 付き結晶が「半長結晶 + 薄レンズ + 半長結晶」を手組みした共振器と
往復行列レベルで厳密一致すること, 無効時 (f=0) の回帰, f→∞ の連続性,
PropOp と PathSegment の 1:1 対応を確認する.
"""
import numpy as np
import pytest

from cavsim.core.cavity import Cavity, PropOp
from cavsim.core.elements import Crystal, CurvedMirror, FlatMirror, ThinLens
from cavsim.core.geometry import build_layout
from cavsim.presets import zfold_ybyag

WL = 1030e-9


def _cav_thermal(brewster, f_th):
    return Cavity(
        [FlatMirror(name="M1", role="end"),
         Crystal(name="X", length=6e-3, n=1.82, brewster=brewster,
                 thermal_f=f_th),
         CurvedMirror(name="M2", roc=0.5, role="end")],
        [0.10, 0.10], wavelength=WL)


def _cav_manual(brewster, f_th):
    """半長結晶 + 薄レンズ + 半長結晶 (間隔ゼロ) の手組み等価系."""
    return Cavity(
        [FlatMirror(name="M1", role="end"),
         Crystal(name="Xa", length=3e-3, n=1.82, brewster=brewster),
         ThinLens(name="TL", f=f_th),
         Crystal(name="Xb", length=3e-3, n=1.82, brewster=brewster),
         CurvedMirror(name="M2", roc=0.5, role="end")],
        [0.10, 0.0, 0.0, 0.10], wavelength=WL)


@pytest.mark.parametrize("brewster", [True, False])
def test_thermal_lens_equals_manual_split(brewster):
    f_th = 0.150
    c1, c2 = _cav_thermal(brewster, f_th), _cav_manual(brewster, f_th)
    for p in ("t", "s"):
        np.testing.assert_allclose(c1.round_trip_matrix(p),
                                   c2.round_trip_matrix(p), atol=1e-12)


def test_thermal_off_is_regression_safe():
    """f=0 では v0.1 と同一構造 (結晶は単一 PropOp) かつ行列が一致."""
    c_off = _cav_thermal(True, 0.0)
    c_ref = Cavity(
        [FlatMirror(name="M1", role="end"),
         Crystal(name="X", length=6e-3, n=1.82, brewster=True),
         CurvedMirror(name="M2", roc=0.5, role="end")],
        [0.10, 0.10], wavelength=WL)
    props = [op for op in c_off.forward_ops() if isinstance(op, PropOp)]
    assert len(props) == 3                      # 間隔2 + 結晶1 (分割なし)
    for p in ("t", "s"):
        np.testing.assert_allclose(c_off.round_trip_matrix(p),
                                   c_ref.round_trip_matrix(p), atol=1e-15)


def test_thermal_lens_continuity_weak_limit():
    """f→∞ で無レンズに連続的に接続する."""
    c_weak = _cav_thermal(True, 1e6)
    c_off = _cav_thermal(True, 0.0)
    for p in ("t", "s"):
        m1, m0 = c_weak.round_trip_matrix(p), c_off.round_trip_matrix(p)
        assert np.max(np.abs(m1 - m0)) < 1e-5


def test_thermal_lens_changes_stability():
    cav = zfold_ybyag()
    cr = next(el for el in cav.elements if isinstance(el, Crystal))
    m0 = cav.compute(max_step=5e-3).m
    cr.thermal_f = 0.200
    m1 = cav.compute(max_step=5e-3).m
    assert abs(m1["t"] - m0["t"]) > 1e-3 and abs(m1["s"] - m0["s"]) > 1e-3


def test_propops_match_segments_with_thermal():
    """熱レンズ有効時も PropOp と PathSegment が個数・長さで 1:1."""
    cav = _cav_thermal(True, 0.150)
    props = [op for op in cav.forward_ops() if isinstance(op, PropOp)]
    _, segs = build_layout(cav)
    assert len(props) == len(segs)
    for op, seg in zip(props, segs):
        assert op.geo_len == pytest.approx(seg.length, rel=1e-12)
    res = cav.compute(max_step=2e-3)
    assert len(res.op_slices) == len(segs)
