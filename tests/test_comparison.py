"""予測-実測比較ワークフローの検証.

実測データはまだ無いため、モデル自身から生成した合成測定で
配管 (位置解決・比・偏差・テンプレート読込) を検証する。
実データとの照合は docs/VALIDATION.md の手順に従い別途行う。
"""
import json

import numpy as np
import pytest

from cavsim.analysis.comparison import compare, load_measurements
from cavsim.presets import simple_linear, zfold_ybyag


def _synthetic_measurements(cav, scale=1.0, err_um=10.0):
    res = cav.compute(max_step=1e-3)
    pts = []
    for i, el in enumerate(cav.elements):
        for k, plane in ((0, "t"), (1, "s")):
            pts.append({"element": el.name, "plane": plane,
                        "w_um": res.element_w[i][k] * 1e6 * scale,
                        "err_um": err_um, "method": "synthetic"})
    return {"schema_version": 1, "points": pts}


def test_self_consistency_ratio_one():
    """モデル自身からの合成測定 → 全行で比=1, 偏差=0σ."""
    cav = zfold_ybyag()
    rep = compare(cav, _synthetic_measurements(cav))
    assert rep.mean_ratio == pytest.approx(1.0, rel=1e-9)
    assert rep.max_abs_deviation_sigma == pytest.approx(0.0, abs=1e-9)
    assert len(rep.rows) == 2 * len(cav.elements)


def test_scaled_measurements_detected():
    """1.10 倍した合成測定 → 平均比 1.10 を正しく報告."""
    cav = zfold_ybyag()
    rep = compare(cav, _synthetic_measurements(cav, scale=1.10))
    assert rep.mean_ratio == pytest.approx(1.10, rel=1e-9)
    assert all(r.ratio == pytest.approx(1.10, rel=1e-9) for r in rep.rows)


def test_element_and_s_position_agree():
    """素子名指定と s_mm 指定が同じ予測値を返す (端面鏡 OC で確認)."""
    cav = zfold_ybyag()
    res = cav.compute(max_step=1e-3)
    s_oc_mm = res.element_s[-1] * 1e3
    w = res.element_w[-1][0] * 1e6
    meas = {"schema_version": 1, "points": [
        {"element": "OC", "plane": "t", "w_um": w},
        {"s_mm": s_oc_mm, "plane": "t", "w_um": w}]}
    rep = compare(cav, meas)
    assert rep.rows[0].w_pred_um == pytest.approx(rep.rows[1].w_pred_um,
                                                  rel=1e-6)


def test_unknown_element_raises():
    cav = zfold_ybyag()
    meas = {"schema_version": 1,
            "points": [{"element": "存在しない鏡", "plane": "t", "w_um": 100}]}
    with pytest.raises(ValueError, match="見つかりません"):
        compare(cav, meas)


def test_unstable_cavity_raises():
    cav = simple_linear()
    cav.spacings[0] = 0.6                       # L > R で不安定
    meas = {"schema_version": 1,
            "points": [{"element": "HR", "plane": "t", "w_um": 100}]}
    with pytest.raises(ValueError, match="不安定"):
        compare(cav, meas)


def test_template_loads_and_null_rows_skipped(tmp_path):
    """同梱テンプレート: 読込可能で, w_um=null の行はスキップされる."""
    tpl = load_measurements("examples/measurements_template.json")
    assert tpl["points"], "テンプレートに points が必要"
    # null 行のみのコピーを作ると「有効な測定点がありません」
    empty = {"schema_version": 1,
             "points": [dict(p, w_um=None) for p in tpl["points"]]}
    f = tmp_path / "empty.json"
    f.write_text(json.dumps(empty), encoding="utf-8")
    with pytest.raises(ValueError, match="有効な測定点"):
        compare(zfold_ybyag(), load_measurements(f))
