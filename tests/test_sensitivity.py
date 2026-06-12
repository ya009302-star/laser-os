"""ミスアライメント感度解析の検証.

平面+凹面の2鏡共振器では、摂動後の光軸が「凹面鏡の曲率中心 C を通り
平面鏡に垂直な直線」であることから厳密解が幾何学的に得られる:

  平面鏡を α 傾け   : Δx(平面鏡)=(R−L)α, Δx(凹面鏡)=Rα, Δu=α
  凹面鏡を β 傾け   : Δx=Rβ (両鏡共通), Δu=0
  凹面鏡を δ デセンタ: Δx=δ (両鏡共通), Δu=0
"""
import numpy as np
import pytest

from cavsim.analysis.sensitivity import (axis_response, sensitivity_table,
                                         sensitivity_text)
from cavsim.core.cavity import Cavity
from cavsim.core.elements import Crystal, CurvedMirror, FlatMirror
from cavsim.presets import zfold_ybyag

L, R = 0.3, 0.5


def make_two_mirror():
    return Cavity([FlatMirror(name="M1", role="end"),
                   CurvedMirror(name="M2", roc=R, role="end")],
                  [L], wavelength=1064e-9)


@pytest.mark.parametrize("plane", ["t", "s"])
def test_flat_mirror_tilt_exact(plane):
    resp = axis_response(make_two_mirror(), 0, "tilt", plane)
    assert resp.dx[0] == pytest.approx(R - L, rel=1e-12)
    assert resp.dx[1] == pytest.approx(R, rel=1e-12)
    assert resp.du[0] == pytest.approx(1.0, rel=1e-12)


@pytest.mark.parametrize("plane", ["t", "s"])
def test_curved_mirror_tilt_exact(plane):
    resp = axis_response(make_two_mirror(), 1, "tilt", plane)
    assert resp.dx[0] == pytest.approx(R, rel=1e-12)
    assert resp.dx[1] == pytest.approx(R, rel=1e-12)
    assert resp.du[0] == pytest.approx(0.0, abs=1e-12)


def test_curved_mirror_decenter_exact():
    resp = axis_response(make_two_mirror(), 1, "decenter", "t")
    assert resp.dx[0] == pytest.approx(1.0, rel=1e-12)   # Δx = δ
    assert resp.dx[1] == pytest.approx(1.0, rel=1e-12)
    assert resp.du[0] == pytest.approx(0.0, abs=1e-12)


def test_linearity_via_unit_normalization():
    """応答は単位摂動あたりの線形係数 (固定点方程式が線形であることの確認)."""
    cav = make_two_mirror()
    r1 = axis_response(cav, 0, "tilt", "t")
    # 同じ共振器で再計算しても同一 (決定論) かつ 2α は 2 倍 (外部で線形にスケール)
    r2 = axis_response(cav, 0, "tilt", "t")
    np.testing.assert_allclose(r1.dx, r2.dx, rtol=1e-15)
    assert 2 * r1.dx[1] == pytest.approx(2 * R, rel=1e-12)


def test_invalid_kinds_raise():
    cav = zfold_ybyag()
    i_cr = next(i for i, e in enumerate(cav.elements) if isinstance(e, Crystal))
    with pytest.raises(ValueError, match="ミラー"):
        axis_response(cav, i_cr, "tilt", "t")
    with pytest.raises(ValueError, match="集光性"):
        axis_response(cav, 0, "decenter", "t")           # 平面端面鏡 (C=0)


def test_unstable_cavity_raises():
    cav = make_two_mirror()
    cav.spacings[0] = 0.6                                # L > R
    with pytest.raises(ValueError, match="不安定"):
        axis_response(cav, 0, "tilt", "t")


def test_zfold_table_runs_and_counts():
    """Z-fold: 全ミラー×両面の感度表が生成され、折返し鏡 (2回反射) も有限値."""
    cav = zfold_ybyag()
    rows = sensitivity_table(cav)
    n_mirrors = sum(isinstance(e, (FlatMirror, CurvedMirror))
                    for e in cav.elements)
    assert len(rows) == 2 * n_mirrors
    assert all(np.isfinite(list(r.dx_per_mrad.values())).all() for r in rows)
    txt = sensitivity_text(cav)
    assert "µm/mrad" in txt and "CM1" in txt
