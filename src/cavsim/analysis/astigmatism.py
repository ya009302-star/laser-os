"""非点収差補償角の計算.

Z-fold/X-fold 共振器でブリュースター結晶の非点収差 (ΔL = ℓ/n − ℓ/n³) を
折返し凹面鏡の非点収差 (Δf = f/cosθ − f·cosθ) で打ち消す折返し角を求める.

閉形式 (第一次近似, 縮約光路長差の釣り合い):
    Σ_i (R_i/2)·sinθ_i·tanθ_i = ΔL
等角・等曲率の k 枚鏡では
    cosθ = sqrt(1 + M²) − M,  M = ΔL / (k·R)
(k=2 のとき arXiv:1501.01158 Eq.(10), Kogelnik et al. 1972 系の標準設計則と一致)

`find_compensation_angle` は閉形式に頼らず, 本パッケージの厳密な往復行列で
数値的に最適角を探索する. 閉形式との一致は tests/test_astigmatism.py で照合済み.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from ..core.cavity import Cavity
from ..core.elements import Crystal, CurvedMirror


def slab_astig_delta(length: float, n: float) -> float:
    """ブリュースタースラブの縮約光路長差 ΔL = ℓ/n − ℓ/n³ [m]."""
    return length / n - length / n**3


def mirror_astig_delta(roc: float, aoi_rad: float) -> float:
    """斜入射凹面鏡の焦点距離差 Δf = f_s − f_t = (R/2)(1/cosθ − cosθ) [m]."""
    c = np.cos(aoi_rad)
    return (roc / 2.0) * (1.0 / c - c)


def compensation_angle(roc: float, length: float, n: float,
                       n_mirrors: int = 2) -> float:
    """補償角 θ [rad] の閉形式解 (等角・等曲率の n_mirrors 枚折返し鏡).

    k·(R/2)·sinθ·tanθ = ΔL を解く. ΔL=0 なら θ=0.
    """
    if roc <= 0 or n_mirrors < 1:
        raise ValueError("roc>0, n_mirrors>=1 が必要です")
    m = slab_astig_delta(length, n) / (n_mirrors * roc)
    c = np.sqrt(1.0 + m * m) - m
    return float(np.arccos(np.clip(c, -1.0, 1.0)))


@dataclass
class CompensationResult:
    theta_deg: float          # 最適折返し角 [deg]
    metric: str               # 使用した評価指標
    metric_value: float       # 最適角での指標値
    theta_grid_deg: np.ndarray
    metric_grid: np.ndarray


def _metric_value(cav: Cavity, metric: str, i_crystal: int | None) -> float:
    res = cav.compute(max_step=5e-3)
    if metric == "match_m":
        return abs(res.m["t"] - res.m["s"])
    if metric == "round_waist":
        if not (res.stable["t"] and res.stable["s"]) or i_crystal is None:
            return float("inf")
        wt, ws = res.element_w[i_crystal]
        if not (np.isfinite(wt) and np.isfinite(ws)) or ws <= 0:
            return float("inf")
        return abs(float(np.log(wt / ws)))
    raise ValueError(f"未知の metric: {metric}")


def find_compensation_angle(cav: Cavity, metric: str = "match_m",
                            theta_range_deg: tuple = (0.5, 25.0),
                            n_grid: int = 200) -> CompensationResult:
    """厳密な往復行列で補償角を数値探索する (numpy のみ使用).

    すべての折返し凹面鏡 (CurvedMirror, role='fold') を共通角 θ に設定して
    指標を最小化する. 等角でない設計には適用しないこと.

    metric:
      'match_m'     : |m_t − m_s| を最小化 (安定領域の整列, 既定)
      'round_waist' : 結晶中心での |ln(w_t/w_s)| を最小化 (真円モード)
    """
    folds = [el for el in cav.elements
             if isinstance(el, CurvedMirror) and el.role == "fold"]
    if not folds:
        raise ValueError("折返し凹面鏡 (CurvedMirror, role='fold') がありません")
    i_crystal = next((i for i, el in enumerate(cav.elements)
                      if isinstance(el, Crystal)), None)

    work = copy.deepcopy(cav)
    work_folds = [el for el in work.elements
                  if isinstance(el, CurvedMirror) and el.role == "fold"]

    def evaluate(theta_deg: float) -> float:
        for el in work_folds:
            el.aoi_deg = float(theta_deg)
        try:
            return _metric_value(work, metric, i_crystal)
        except Exception:                              # noqa: BLE001
            return float("inf")

    thetas = np.linspace(theta_range_deg[0], theta_range_deg[1], n_grid)
    values = np.array([evaluate(t) for t in thetas])
    if not np.isfinite(values).any():
        raise RuntimeError("探索範囲内で評価可能な角度がありません")
    k = int(np.nanargmin(values))
    best_t, best_v = float(thetas[k]), float(values[k])

    # 3点パラボラ補間で精密化 (端点でなく近傍が有限のときのみ)
    if 0 < k < n_grid - 1 and np.isfinite(values[k - 1]) and np.isfinite(values[k + 1]):
        x0, x1, x2 = thetas[k - 1], thetas[k], thetas[k + 1]
        y0, y1, y2 = values[k - 1], values[k], values[k + 1]
        denom = (y0 - 2 * y1 + y2)
        if abs(denom) > 1e-30:
            xv = x1 + 0.5 * (x0 - x2) * (y0 - y2) / (2 * denom)
            if x0 < xv < x2:
                yv = evaluate(float(xv))
                if yv < best_v:
                    best_t, best_v = float(xv), float(yv)

    return CompensationResult(theta_deg=best_t, metric=metric,
                              metric_value=best_v,
                              theta_grid_deg=thetas, metric_grid=values)
