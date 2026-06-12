"""2D スタビリティマップと安定許容差の検証."""
import numpy as np
import pytest

from cavsim.analysis.scan import (scan_spacing, scan_spacing_2d,
                                  stability_margins, stability_ranges)
from cavsim.core.cavity import Cavity
from cavsim.core.elements import CurvedMirror, FlatMirror
from cavsim.presets import zfold_ybyag


def make_plano_concave(L=0.3, R=0.5):
    return Cavity([FlatMirror(name="M1", role="end"),
                   CurvedMirror(name="M2", roc=R, role="end")],
                  [L], wavelength=1064e-9)


def test_2d_map_row_matches_1d_scan():
    """2D マップの 1 行が同条件の 1D スキャンと一致 (Z-fold, d1×d2)."""
    cav = zfold_ybyag()
    va = np.linspace(0.045, 0.060, 7)        # d1: CM1–結晶
    vb = np.linspace(0.045, 0.060, 9)        # d2: 結晶–CM2
    out2d = scan_spacing_2d(cav, 1, 2, va, vb)
    i_fix = 3
    import copy
    work = copy.deepcopy(cav)
    work.spacings[1] = float(va[i_fix])
    out1d = scan_spacing(work, 2, vb)
    np.testing.assert_allclose(out2d["m_t"][i_fix], out1d["m_t"],
                               rtol=0, atol=1e-12)
    np.testing.assert_allclose(out2d["m_s"][i_fix], out1d["m_s"],
                               rtol=0, atol=1e-12)
    assert out2d["stable"].shape == (7, 9)
    assert out2d["stable"].any()             # プリセット近傍に安定領域がある


def test_2d_same_index_raises():
    with pytest.raises(ValueError):
        scan_spacing_2d(zfold_ybyag(), 1, 1, np.array([0.05]),
                        np.array([0.05]))


def test_margins_plano_concave_edge_at_R():
    """平凹共振器 L=0.3, R=0.5: 増加方向の境界は L=R (マージン 0.2 m)。
    減少方向は L→0 まで安定 (g₂→1, m→1⁻) なので探索範囲内に境界なし。"""
    margins = stability_margins(make_plano_concave(), rel_range=0.9)
    down, up = margins[0]
    assert down is None
    assert up == pytest.approx(0.2, abs=1e-4)


def test_margins_zfold_match_known_band():
    """Z-fold d1=50.55mm 単独掃引: 安定帯 ≈48.79–52.42mm (d2 は固定のまま)。
    ※ v0.1 例の設計時に使った 49.7–51.4mm は d1, d2 を対称に同時掃引した
    帯であり、ここでの単独掃引とは異なる。"""
    cav = zfold_ybyag()
    margins = stability_margins(cav, rel_range=0.3)
    down, up = margins[1]                    # d1: CM1–結晶
    assert down is not None and up is not None
    assert 1.5e-3 < down < 2.2e-3            # ≈ 50.55 − 48.79 = 1.77 mm
    assert 1.5e-3 < up < 2.2e-3              # ≈ 52.42 − 50.55 = 1.88 mm
    # 1D スキャンの安定帯端と二分法マージンの整合 (粗い照合)
    vals = np.linspace(0.048, 0.053, 400)
    out = scan_spacing(cav, 1, vals)
    rng = stability_ranges(out["values"], out["m_t"], out["m_s"])
    band = next(r for r in rng if r[0] < cav.spacings[1] < r[1])
    assert cav.spacings[1] - band[0] == pytest.approx(down, abs=2e-5)
    assert band[1] - cav.spacings[1] == pytest.approx(up, abs=2e-5)


def test_margins_unstable_raises():
    cav = make_plano_concave(L=0.6)
    with pytest.raises(ValueError, match="不安定"):
        stability_margins(cav)
