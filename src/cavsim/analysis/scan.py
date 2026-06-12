"""パラメータスキャン: 間隔や素子パラメータを掃引して安定性とモード径を解析する."""
from __future__ import annotations

import copy
import numpy as np

from ..core.cavity import Cavity
from ..core import beam


def scan_spacing(cav: Cavity, spacing_index: int, values_m: np.ndarray,
                 target_element: int | None = None) -> dict:
    """spacings[spacing_index] を values_m で掃引する.

    Returns: dict(values, m_t, m_s, w_t, w_s)
      w_* は target_element 位置でのビーム半径 [m] (None なら最小ウエスト)
    """
    work = copy.deepcopy(cav)
    out = {k: np.full(len(values_m), np.nan) for k in ("m_t", "m_s", "w_t", "w_s")}
    for i, v in enumerate(values_m):
        work.spacings[spacing_index] = float(v)
        try:
            res = work.compute(max_step=2e-3)
        except Exception:
            continue
        out["m_t"][i], out["m_s"][i] = res.m["t"], res.m["s"]
        if target_element is not None and 0 <= target_element < len(res.element_w):
            out["w_t"][i], out["w_s"][i] = res.element_w[target_element]
        else:
            out["w_t"][i] = np.nanmin(res.w["t"]) if res.stable["t"] else np.nan
            out["w_s"][i] = np.nanmin(res.w["s"]) if res.stable["s"] else np.nan
    out["values"] = np.asarray(values_m)
    return out


def stability_ranges(values: np.ndarray, m_t: np.ndarray, m_s: np.ndarray):
    """両面とも |m|<1 となる値の区間 [(v0, v1), ...] を返す."""
    ok = (np.abs(m_t) < 1) & (np.abs(m_s) < 1)
    ranges, start = [], None
    for i, flag in enumerate(ok):
        if flag and start is None:
            start = values[i]
        elif not flag and start is not None:
            ranges.append((start, values[i - 1]))
            start = None
    if start is not None:
        ranges.append((start, values[-1]))
    return ranges


def _stable_both(work: Cavity) -> bool:
    """両面とも |m|<1 か (固有モード計算なしの高速判定)."""
    for p in ("t", "s"):
        if abs(beam.stability_parameter(work.round_trip_matrix(p))) >= 1.0:
            return False
    return True


def scan_spacing_2d(cav: Cavity, idx_a: int, idx_b: int,
                    values_a: np.ndarray, values_b: np.ndarray) -> dict:
    """間隔 2 つを同時掃引し、安定性パラメータの 2D マップを返す.

    Returns: dict(values_a, values_b, m_t, m_s, stable)
      m_* は shape (len(values_a), len(values_b))。stable は両面 |m|<1。
      固有モード計算を省き往復行列のみ評価するため高速。
    """
    if idx_a == idx_b:
        raise ValueError("異なる間隔インデックスを指定してください")
    work = copy.deepcopy(cav)
    na, nb = len(values_a), len(values_b)
    m_t = np.full((na, nb), np.nan)
    m_s = np.full((na, nb), np.nan)
    for i, va in enumerate(values_a):
        work.spacings[idx_a] = float(va)
        for j, vb in enumerate(values_b):
            work.spacings[idx_b] = float(vb)
            try:
                m_t[i, j] = beam.stability_parameter(
                    work.round_trip_matrix("t"))
                m_s[i, j] = beam.stability_parameter(
                    work.round_trip_matrix("s"))
            except Exception:                          # noqa: BLE001
                continue
    return {"values_a": np.asarray(values_a), "values_b": np.asarray(values_b),
            "m_t": m_t, "m_s": m_s,
            "stable": (np.abs(m_t) < 1) & (np.abs(m_s) < 1)}


def stability_margins(cav: Cavity, rel_range: float = 0.5,
                      n_grid: int = 200, refine_iters: int = 40) -> list:
    """各間隔について、現在値から不安定化までの距離 [m] を返す.

    Returns: [(down, up), ...]  down/up は現在値から減らす/増やす方向の
    マージン。探索範囲 (現在値 × (1±rel_range), 下限 0) 内に不安定境界が
    無ければ None。グリッドで挟んだ後、二分法で精密化する。
    """
    if not _stable_both(cav):
        raise ValueError("現在の構成が不安定なためマージンを定義できません")
    work = copy.deepcopy(cav)
    margins = []
    for k, d0 in enumerate(cav.spacings):
        lo = max(0.0, d0 * (1.0 - rel_range))
        hi = d0 * (1.0 + rel_range)

        def stable_at(v: float) -> bool:
            work.spacings[k] = float(v)
            ok = _stable_both(work)
            work.spacings[k] = d0
            return ok

        def edge(direction: int) -> float | None:
            """direction=-1: 減少方向, +1: 増加方向. 境界までの距離を返す."""
            end = lo if direction < 0 else hi
            grid = np.linspace(d0, end, n_grid)
            bad = next((v for v in grid[1:] if not stable_at(v)), None)
            if bad is None:
                return None
            a, b = d0, bad                              # a: 安定, b: 不安定
            for _ in range(refine_iters):
                mid = 0.5 * (a + b)
                if stable_at(mid):
                    a = mid
                else:
                    b = mid
            return abs(0.5 * (a + b) - d0)

        margins.append((edge(-1), edge(+1)))
    return margins
