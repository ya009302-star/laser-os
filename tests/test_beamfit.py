"""出力ビーム伝搬と z–w フィットの検証."""
import numpy as np
import pytest

from cavsim.analysis.beamfit import fit_caustic, output_beam, output_beam_text
from cavsim.core.cavity import Cavity
from cavsim.core.elements import CurvedMirror, FlatMirror
from cavsim.presets import zfold_ybyag

WL = 1064e-9
L, R = 0.3, 0.5


def make_plano_concave():
    return Cavity([FlatMirror(name="M1", role="end"),
                   CurvedMirror(name="M2", roc=R, role="end")],
                  [L], wavelength=WL)


def test_output_through_flat_end_waist_at_mirror():
    """平凹共振器: ウエストは平面鏡上 → 外部ではウエスト位置 z0=0,
    w0 = 内部解析解, w(z) = w0√(1+(z/zR)²)."""
    cav = make_plano_concave()
    obs = output_beam(cav, end_index=0)
    w0_expect = float(np.sqrt((WL / np.pi) * np.sqrt(L * (R - L))))
    for p in ("t", "s"):
        ob = obs[p]
        assert ob.z_waist == pytest.approx(0.0, abs=1e-12)
        assert ob.w0 == pytest.approx(w0_expect, rel=1e-9)
        assert ob.w_at_mirror == pytest.approx(w0_expect, rel=1e-9)
        zr = np.pi * w0_expect ** 2 / WL
        assert ob.z_rayleigh == pytest.approx(zr, rel=1e-9)
        z = 0.7
        assert float(ob.w_at(z)) == pytest.approx(
            w0_expect * np.sqrt(1 + (z / zr) ** 2), rel=1e-9)


def test_output_matches_internal_w_at_oc_zfold():
    """Z-fold OC: 外部 w(0) が内部の OC 上ビーム径と一致し, t/s で異なる."""
    cav = zfold_ybyag()
    res = cav.compute(max_step=1e-3)
    obs = output_beam(cav)                    # 末尾 = OC
    wt, ws = res.element_w[-1]
    assert obs["t"].w_at_mirror == pytest.approx(wt, rel=1e-3)
    assert obs["s"].w_at_mirror == pytest.approx(ws, rel=1e-3)
    assert abs(obs["t"].w_at_mirror / obs["s"].w_at_mirror - 1) > 0.05
    txt = output_beam_text(cav)
    assert "OC" in txt and "µm" in txt


def test_curved_end_raises():
    cav = make_plano_concave()
    with pytest.raises(ValueError, match="曲面端面鏡"):
        output_beam(cav, end_index=1)


def test_unstable_raises():
    cav = make_plano_concave()
    cav.spacings[0] = 0.6
    with pytest.raises(ValueError, match="不安定"):
        output_beam(cav, end_index=0)


def test_fit_recovers_ideal_gaussian():
    """合成 M²=1 データ → w0, z0, M² を高精度で復元."""
    cav = make_plano_concave()
    ob = output_beam(cav, end_index=0)["t"]
    z = np.linspace(0.05, 1.2, 25)
    fit = fit_caustic(z, ob.w_at(z), WL)
    assert fit.w0 == pytest.approx(ob.w0, rel=1e-6)
    assert fit.z0 == pytest.approx(0.0, abs=1e-9)
    assert fit.m2 == pytest.approx(1.0, rel=1e-6)
    assert fit.rms_residual < 1e-12


def test_fit_recovers_m2():
    """発散を M² 倍した合成データ → M² を復元."""
    wl, w0, z0, m2_true = 1030e-9, 250e-6, 0.10, 1.30
    theta = m2_true * wl / (np.pi * w0)
    z = np.linspace(-0.2, 1.0, 30)
    w = np.sqrt(w0 ** 2 + theta ** 2 * (z - z0) ** 2)
    fit = fit_caustic(z, w, wl)
    assert fit.m2 == pytest.approx(m2_true, rel=1e-9)
    assert fit.w0 == pytest.approx(w0, rel=1e-9)
    assert fit.z0 == pytest.approx(z0, rel=1e-9)


def test_fit_error_paths():
    with pytest.raises(ValueError, match="3 点"):
        fit_caustic([0.0, 0.1], [1e-4, 2e-4], WL)
    with pytest.raises(ValueError, match="広がり"):
        fit_caustic([0.1, 0.1, 0.1], [1e-4, 1e-4, 1e-4], WL)
    z = np.linspace(0, 1, 10)
    with pytest.raises(ValueError, match="a≤0"):
        fit_caustic(z, np.full(10, 1e-4) - 1e-5 * z ** 2, WL)
