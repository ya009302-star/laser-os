"""材料分散と往復 GDD/TOD 記帳の検証.

- 溶融石英 (Malitson 1965) の屈折率を既知値と照合
- λ 微分公式 (k₂, k₃) を ω 軸の直接数値微分と相互照合 (実装の内部整合性)
- 文献でよく知られたアンカー値: 溶融石英 GVD ≈ +36 fs²/mm @800nm,
  ゼロ分散波長が 1.2–1.35 µm 帯にあること
- source_status='estimated' 使用時の警告
- 往復記帳の手計算照合と JSON 往復
"""
import numpy as np
import pytest

from cavsim.analysis.dispersion import round_trip_dispersion
from cavsim.core.cavity import Cavity
from cavsim.core.elements import Crystal, CurvedMirror, FlatMirror
from cavsim.core.materials import (C_LIGHT, MATERIALS, Material,
                                   add_material, get_material)
from cavsim.io import project

FS = get_material("fused_silica")


def test_fused_silica_index_anchor():
    """n_d (587.6 nm) ≈ 1.4585 (Malitson 1965)."""
    assert FS.n(587.6e-9) == pytest.approx(1.4585, abs=1e-3)


def test_gvd_lambda_form_matches_omega_derivative():
    """k₂(λ式) と k(ω)=n·ω/c の ω 直接2階差分が一致 (内部整合性)."""
    for wl in (0.6e-6, 0.8e-6, 1.03e-6, 1.5e-6):
        w0 = 2 * np.pi * C_LIGHT / wl
        h = w0 * 1e-5
        k = lambda w: FS._n_um(2 * np.pi * C_LIGHT / w * 1e6) * w / C_LIGHT
        k2_num = (k(w0 - h) - 2 * k(w0) + k(w0 + h)) / h**2
        assert FS.gvd(wl) == pytest.approx(k2_num, rel=1e-4)


def test_tod_lambda_form_matches_omega_derivative():
    wl = 0.8e-6
    w0 = 2 * np.pi * C_LIGHT / wl
    h = w0 * 2e-4
    k = lambda w: FS._n_um(2 * np.pi * C_LIGHT / w * 1e6) * w / C_LIGHT
    k3_num = (-k(w0 - 2*h) + 2*k(w0 - h) - 2*k(w0 + h) + k(w0 + 2*h)) / (2*h**3)
    assert FS.tod_per_length(wl) == pytest.approx(k3_num, rel=1e-3)


def test_fused_silica_gvd_literature_anchor():
    """+36 fs²/mm 前後 @800nm (広く表化された値) とゼロ分散の 1.2–1.35 µm 通過."""
    gvd_800 = FS.gvd(800e-9) * 1e30 / 1e3          # [fs²/mm]
    assert 35.0 < gvd_800 < 37.5
    assert FS.gvd(1.20e-6) > 0 and FS.gvd(1.35e-6) < 0


def test_estimated_material_warns():
    add_material(Material(
        name="_dummy_est", sellmeier_b=(1.0,), sellmeier_c_um2=(0.01,),
        range_um=(0.4, 2.0), source_status="estimated",
        source="テスト用ダミー (実材料ではない)"))
    try:
        with pytest.warns(UserWarning, match="estimated"):
            get_material("_dummy_est").n(1.0e-6)
    finally:
        MATERIALS.pop("_dummy_est", None)


def test_unknown_material_raises():
    with pytest.raises(KeyError):
        get_material("yb_yag")                      # 出典提供までは未登録


def test_round_trip_accounting_hand_count():
    """端鏡×1, 折返し鏡×2, 結晶×2通過 (材料 + 追加分) の手計算照合."""
    wl = 1030e-9
    cr = Crystal(name="FS板", length=2e-3, n=1.45, brewster=True,
                 material="fused_silica", gdd_fs2=10.0)
    cav = Cavity(
        [FlatMirror(name="HR", role="end", gdd_fs2=-50.0),
         CurvedMirror(name="CM", roc=0.1, role="fold", gdd_fs2=-100.0),
         cr,
         FlatMirror(name="OC", role="end", gdd_fs2=0.0)],
        [0.1, 0.05, 0.5], wavelength=wl)
    rep = round_trip_dispersion(cav)
    per_pass = FS.gvd(wl) * cr.length * 1e30 + 10.0
    expect = (-50.0) * 1 + (-100.0) * 2 + per_pass * 2 + 0.0
    assert rep.gdd_total_fs2 == pytest.approx(expect, rel=1e-12)
    assert "fused_silica" in rep.to_text()


def test_dispersion_fields_json_roundtrip(tmp_path):
    cav = Cavity(
        [FlatMirror(name="HR", role="end", gdd_fs2=-40.0, tod_fs3=5.0),
         Crystal(name="X", length=3e-3, n=1.82, material="fused_silica",
                 gdd_fs2=1.5),
         FlatMirror(name="OC", role="end")],
        [0.1, 0.1], wavelength=1030e-9)
    f = tmp_path / "d.json"
    project.save(cav, f)
    cav2 = project.load(f)
    assert cav2.elements[0].gdd_fs2 == -40.0
    assert cav2.elements[0].tod_fs3 == 5.0
    assert cav2.elements[1].material == "fused_silica"
    r1, r2 = round_trip_dispersion(cav), round_trip_dispersion(cav2)
    assert r1.gdd_total_fs2 == pytest.approx(r2.gdd_total_fs2, rel=1e-12)
