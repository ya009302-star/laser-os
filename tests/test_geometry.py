"""3D 配置の検証: ブリュースター横変位の解析式照合と経路の連続性."""
import numpy as np
import pytest

from cavsim.core.cavity import Cavity
from cavsim.core.elements import Crystal, FlatMirror
from cavsim.core.geometry import build_layout
from cavsim.presets import zfold_ybyag


def straight_with_crystal(brewster=True, tilt=1, l=5e-3, n=1.82):
    return Cavity(
        [FlatMirror(name="M1", role="end"),
         Crystal(name="X", length=l, n=n, brewster=brewster, tilt=tilt),
         FlatMirror(name="M2", role="end")],
        [0.10, 0.10], wavelength=1030e-9)


def test_brewster_lateral_displacement_formula():
    """横変位 = ℓ(n²−1)/(n²+1), 軸方向前進 = 2nℓ/(n²+1), 出射方向は不変."""
    l, n = 5e-3, 1.82
    cav = straight_with_crystal(brewster=True, tilt=1, l=l, n=n)
    poses, segs = build_layout(cav)
    # 結晶セグメント (segs[1]) の終端 = M2 直前の経路始点
    end = segs[1].start + segs[1].direction * segs[1].length
    along = end[0] - segs[1].start[0]
    lateral = end[1] - segs[1].start[1]
    assert along == pytest.approx(2 * n * l / (n**2 + 1), rel=1e-12)
    assert abs(lateral) == pytest.approx(l * (n**2 - 1) / (n**2 + 1), rel=1e-12)
    assert np.hypot(along, lateral) == pytest.approx(l, rel=1e-12)
    # 出射方向は入射と平行 (+x)
    np.testing.assert_allclose(segs[2].direction, [1, 0, 0], atol=1e-12)
    # 末端鏡が横変位した位置にある
    np.testing.assert_allclose(poses[-1].position[1], lateral, rtol=1e-12)


def test_tilt_sign_flips_lateral_side():
    p_plus, _ = build_layout(straight_with_crystal(tilt=1))
    p_minus, _ = build_layout(straight_with_crystal(tilt=-1))
    y_plus = p_plus[-1].position[1]
    y_minus = p_minus[-1].position[1]
    assert y_plus == pytest.approx(-y_minus, rel=1e-12)
    assert abs(y_plus) > 0


def test_normal_incidence_no_displacement():
    poses, segs = build_layout(straight_with_crystal(brewster=False))
    np.testing.assert_allclose(poses[-1].position[1:], [0, 0], atol=1e-15)
    np.testing.assert_allclose(segs[1].direction, [1, 0, 0], atol=1e-15)


def test_path_continuity_and_total_length_zfold():
    """Z-fold (横変位込み): 全セグメントが連続し, 幾何全長が compute() と一致."""
    cav = zfold_ybyag()
    poses, segs = build_layout(cav)
    for a, b in zip(segs[:-1], segs[1:]):
        end = a.start + a.direction * a.length
        np.testing.assert_allclose(end, b.start, atol=1e-12)
    total = sum(s.length for s in segs)
    res = cav.compute(max_step=5e-3)
    assert total == pytest.approx(res.total_length, rel=1e-12)
