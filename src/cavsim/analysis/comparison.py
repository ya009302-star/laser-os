"""予測 (cavsim) と実測モード径の比較ワークフロー.

測定記録 JSON (schema_version=1):
{
  "schema_version": 1,
  "date": "YYYY-MM-DD",
  "instrument": "ビームプロファイラ型番など",
  "notes": "測定条件",
  "points": [
    {"element": "OC", "plane": "t", "w_um": 430.0, "err_um": 20.0,
     "method": "knife-edge"},
    {"s_mm": 850.0, "plane": "s", "w_um": 520.0}
  ]
}

各点は素子名 (element) または経路座標 (s_mm, 素子0表面=0) で位置指定する。
plane は "t" / "s"。w_um は 1/e² 半径 [µm]。

注意: 本モジュールは比較レポートを生成するのみであり、検証状態
(docs/VALIDATION.md) の更新は人間が測定の妥当性を確認した上で行うこと。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..core.cavity import Cavity

SCHEMA_VERSION = 1


@dataclass
class ComparisonRow:
    label: str                # 位置 (素子名 or s)
    plane: str                # 't' / 's'
    w_meas_um: float
    w_pred_um: float
    err_um: float | None      # 測定誤差 (1σ), 無ければ None
    method: str = ""

    @property
    def ratio(self) -> float:
        return self.w_meas_um / self.w_pred_um

    @property
    def deviation_sigma(self) -> float | None:
        if self.err_um is None or self.err_um <= 0:
            return None
        return (self.w_meas_um - self.w_pred_um) / self.err_um


@dataclass
class ComparisonReport:
    rows: list

    @property
    def mean_ratio(self) -> float:
        return float(np.mean([r.ratio for r in self.rows]))

    @property
    def max_abs_deviation_sigma(self) -> float | None:
        devs = [abs(r.deviation_sigma) for r in self.rows
                if r.deviation_sigma is not None]
        return max(devs) if devs else None

    def to_text(self) -> str:
        lines = [f"{'位置':<12}{'面':>3}{'実測w[µm]':>11}{'予測w[µm]':>11}"
                 f"{'比':>8}{'偏差[σ]':>9}  手法"]
        for r in self.rows:
            dev = f"{r.deviation_sigma:+.2f}" if r.deviation_sigma is not None \
                else "  -"
            lines.append(f"{r.label:<12}{r.plane:>3}{r.w_meas_um:>11.1f}"
                         f"{r.w_pred_um:>11.1f}{r.ratio:>8.3f}{dev:>9}"
                         f"  {r.method}")
        lines.append(f"平均比 = {self.mean_ratio:.3f}"
                     + (f", 最大偏差 = {self.max_abs_deviation_sigma:.2f}σ"
                        if self.max_abs_deviation_sigma is not None else ""))
        return "\n".join(lines)


def load_measurements(path: str | Path) -> dict:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if d.get("schema_version", 1) > SCHEMA_VERSION:
        raise ValueError("未対応の測定スキーマバージョン")
    if "points" not in d or not isinstance(d["points"], list):
        raise ValueError("'points' 配列がありません")
    return d


def _predict_w(cav: Cavity, res, point: dict) -> tuple[str, float]:
    """測定点に対応する予測 w [m] を返す. 戻り値: (ラベル, w)."""
    plane = point["plane"]
    if plane not in ("t", "s"):
        raise ValueError(f"plane は 't'/'s': {plane}")
    if "element" in point:
        names = [el.name for el in cav.elements]
        if point["element"] not in names:
            raise ValueError(
                f"素子 '{point['element']}' が見つかりません (存在: {names})")
        i = names.index(point["element"])
        w_ts = res.element_w[i]
        return point["element"], w_ts[0] if plane == "t" else w_ts[1]
    if "s_mm" in point:
        s = float(point["s_mm"]) * 1e-3
        if not (res.s_axis[0] <= s <= res.s_axis[-1]):
            raise ValueError(f"s={point['s_mm']} mm が経路範囲外です")
        w = float(np.interp(s, res.s_axis, res.w[plane]))
        return f"s={point['s_mm']:g}mm", w
    raise ValueError("各測定点には 'element' か 's_mm' が必要です")


def compare(cav: Cavity, measurements: dict) -> ComparisonReport:
    res = cav.compute(max_step=1e-3)
    if not (res.stable["t"] and res.stable["s"]):
        raise ValueError("共振器が不安定なため予測モード径を計算できません")
    rows = []
    for pt in measurements["points"]:
        if pt.get("w_um") is None:
            continue                                   # テンプレートの未記入行
        label, w_pred = _predict_w(cav, res, pt)
        rows.append(ComparisonRow(
            label=label, plane=pt["plane"],
            w_meas_um=float(pt["w_um"]), w_pred_um=w_pred * 1e6,
            err_um=pt.get("err_um"), method=pt.get("method", "")))
    if not rows:
        raise ValueError("有効な測定点がありません (w_um がすべて未記入)")
    return ComparisonReport(rows=rows)
