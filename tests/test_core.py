"""コア物理の検証テスト. 解析解が既知の系と比較する."""
import numpy as np
import pytest

from cavsim.core import matrices as mat
from cavsim.core import beam
from cavsim.core.cavity import Cavity
from cavsim.core.elements import FlatMirror, CurvedMirror, Crystal, ThinLens
from cavsim.io import project
from cavsim.analysis.scan import scan_spacing, stability_ranges

WL = 1030e-9


def make_plano_concave(L, R):
    return Cavity(
        [FlatMirror(name="M1", role="end"),
         CurvedMirror(name="M2", roc=R, aoi_deg=0.0, role="end")],
        [L], wavelength=WL)


def test_stability_g1g2():
    """m = 2*g1*g2 - 1 (平面+凹面: g1=1, g2=1-L/R)."""
    L, R = 0.3, 0.5
    cav = make_plano_concave(L, R)
    g2 = 1 - L / R
    for p in ("t", "s"):
        m = beam.stability_parameter(cav.round_trip_matrix(p))
        assert m == pytest.approx(2 * 1 * g2 - 1, abs=1e-12)


def test_waist_plano_concave():
    """平面鏡上のウエスト: w0^2 = (λ/π) * sqrt(L*(R-L))."""
    L, R = 0.3, 0.5
    cav = make_plano_concave(L, R)
    res = cav.compute()
    w0_expect = np.sqrt((WL / np.pi) * np.sqrt(L * (R - L)))
    assert res.element_w[0][0] == pytest.approx(w0_expect, rel=1e-3)
    assert res.element_w[0][1] == pytest.approx(w0_expect, rel=1e-3)
    # 凹面鏡上のスポット: w^2 = (λL/π) * sqrt(g1/(g2*(1-g1*g2)))
    g1, g2 = 1.0, 1 - L / R
    w2_expect = np.sqrt((WL * L / np.pi) ** 2 * g1 / (g2 * (1 - g1 * g2)))
    assert res.element_w[1][0] ** 2 == pytest.approx(w2_expect, rel=1e-3)


def test_unstable_detection():
    cav = make_plano_concave(0.6, 0.5)  # L > R で不安定
    res = cav.compute()
    assert not res.stable["t"] and not res.stable["s"]
    assert np.isnan(res.element_w[0][0])


def test_curved_mirror_astigmatism():
    """斜入射凹面鏡: f_t/f_s = cos^2θ."""
    R, th = 0.1, np.deg2rad(15)
    mt = mat.curved_mirror(R, th, "t")
    ms = mat.curved_mirror(R, th, "s")
    ft, fs = -1 / mt[1, 0], -1 / ms[1, 0]
    assert ft / fs == pytest.approx(np.cos(th) ** 2, rel=1e-12)


def test_brewster_reduced_lengths():
    """ブリュースタースラブ: d_t/d_s = 1/n^2, d_s = ℓ/n."""
    l, n = 5e-3, 1.82
    dt = mat.reduced_length_brewster(l, n, "t")
    ds = mat.reduced_length_brewster(l, n, "s")
    assert ds == pytest.approx(l / n, rel=1e-12)
    assert dt / ds == pytest.approx(1 / n**2, rel=1e-12)


def test_crystal_equals_reduced_path():
    """垂直入射結晶入りの共振器 = 等価縮約長の空気共振器."""
    cr = Crystal(name="X", length=10e-3, n=1.82, brewster=False)
    cav1 = Cavity([FlatMirror(role="end"), cr,
                   CurvedMirror(roc=0.5, role="end")], [0.1, 0.1], wavelength=WL)
    d_eq = 0.1 + cr.length / cr.n + 0.1
    cav2 = make_plano_concave(d_eq, 0.5)
    for p in ("t", "s"):
        np.testing.assert_allclose(cav1.round_trip_matrix(p),
                                   cav2.round_trip_matrix(p), atol=1e-12)


def test_roundtrip_determinant():
    cav = Cavity(
        [FlatMirror(name="SESAM", role="end"),
         CurvedMirror(name="CM1", roc=0.1, aoi_deg=8, turn=1, role="fold"),
         Crystal(name="Yb:YAG", length=3e-3, n=1.82, brewster=True),
         CurvedMirror(name="CM2", roc=0.1, aoi_deg=8, turn=-1, role="fold"),
         FlatMirror(name="OC", role="end")],
        [0.25, 0.05, 0.05, 0.6], wavelength=WL)
    for p in ("t", "s"):
        assert np.linalg.det(cav.round_trip_matrix(p)) == pytest.approx(1.0, abs=1e-9)


def test_project_roundtrip(tmp_path):
    cav = Cavity(
        [FlatMirror(name="HR", role="end"), ThinLens(name="L1", f=0.1),
         CurvedMirror(name="OC", roc=0.3, role="end")],
        [0.12, 0.2], wavelength=WL, name="test")
    f = tmp_path / "c.json"
    project.save(cav, f)
    cav2 = project.load(f)
    assert [e.name for e in cav2.elements] == ["HR", "L1", "OC"]
    for p in ("t", "s"):
        np.testing.assert_allclose(cav.round_trip_matrix(p),
                                   cav2.round_trip_matrix(p), atol=1e-12)


def test_scan_finds_stable_zone():
    cav = make_plano_concave(0.3, 0.5)
    vals = np.linspace(0.05, 0.7, 200)
    out = scan_spacing(cav, 0, vals)
    rng = stability_ranges(out["values"], out["m_t"], out["m_s"])
    assert len(rng) == 1
    assert rng[0][0] < 0.1 and rng[0][1] > 0.45  # ほぼ 0 < L < R
