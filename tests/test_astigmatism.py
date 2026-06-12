"""非点収差補償角の検証.

閉形式 (第一次近似) が定義式を満たすこと, および本パッケージの厳密往復行列に
よる数値最適化と閉形式が十分一致することを確認する.
"""
import numpy as np
import pytest

from cavsim.analysis.astigmatism import (
    compensation_angle, find_compensation_angle,
    mirror_astig_delta, slab_astig_delta)
from cavsim.core.elements import Crystal, CurvedMirror
from cavsim.presets import zfold_ybyag


def test_closed_form_satisfies_balance():
    """k 枚鏡: k·Δf(θ) = ΔL を厳密に満たす."""
    roc, length, n = 0.100, 3e-3, 1.82
    for k in (1, 2):
        th = compensation_angle(roc, length, n, n_mirrors=k)
        lhs = k * mirror_astig_delta(roc, th)
        assert lhs == pytest.approx(slab_astig_delta(length, n), rel=1e-12)


def test_zero_slab_gives_zero_angle():
    assert compensation_angle(0.1, 0.0, 1.82) == pytest.approx(0.0, abs=1e-12)


def test_numeric_matches_closed_form_on_zfold():
    """Z-fold プリセット: 数値最適化 (厳密行列) と閉形式が 0.5° 以内で一致."""
    cav = zfold_ybyag()
    cr = next(el for el in cav.elements if isinstance(el, Crystal))
    cm = next(el for el in cav.elements if isinstance(el, CurvedMirror))
    th_cf = np.degrees(compensation_angle(cm.roc, cr.length, cr.n, n_mirrors=2))

    res_m = find_compensation_angle(cav, metric="match_m",
                                    theta_range_deg=(1.0, 15.0), n_grid=150)
    res_w = find_compensation_angle(cav, metric="round_waist",
                                    theta_range_deg=(1.0, 15.0), n_grid=150)
    assert abs(res_m.theta_deg - th_cf) < 0.5
    assert abs(res_w.theta_deg - th_cf) < 0.5
    assert res_m.metric_value < 1e-2          # |m_t−m_s| がほぼゼロ
    assert res_w.metric_value < 1e-2          # w_t/w_s が 1% 以内

    # 閉形式角を実際に適用しても結晶内モードがほぼ真円になること
    import copy
    work = copy.deepcopy(cav)
    for el in work.elements:
        if isinstance(el, CurvedMirror) and el.role == "fold":
            el.aoi_deg = th_cf
    r = work.compute()
    i_cr = next(i for i, el in enumerate(work.elements)
                if isinstance(el, Crystal))
    wt, ws = r.element_w[i_cr]
    assert wt / ws == pytest.approx(1.0, abs=0.02)


def test_requires_fold_mirror():
    from cavsim.presets import simple_linear
    with pytest.raises(ValueError):
        find_compensation_angle(simple_linear())
