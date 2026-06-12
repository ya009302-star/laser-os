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
