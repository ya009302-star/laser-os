"""線形共振器モデル.

elements[0] と elements[-1] は端面鏡であること.
spacings[i] は elements[i] と elements[i+1] の間の空気間隔(表面間) [m].
往復: 素子0で反射した直後の面を基準面とする.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from . import matrices as mat
from . import beam
from .elements import Element

PLANES = mat.PLANES


@dataclass
class PropOp:
    """伝搬区間(空気間隔 or 結晶内部)."""
    geo_len: float                 # 幾何長 [m]
    red_len: dict                  # 面ごとの縮約長 {"t": .., "s": ..}
    n: float                       # 表示用屈折率
    owner: Element | None = None   # 結晶なら素子参照, 空気間隔なら None


@dataclass
class MatOp:
    """点素子の行列作用."""
    element: Element
    index: int                     # elements 内のインデックス


@dataclass
class CaveResult:
    """compute() の結果."""
    stable: dict                   # {"t": bool, "s": bool}
    m: dict                        # 安定性パラメータ {"t": float, "s": float}
    s_axis: np.ndarray             # 経路に沿った幾何座標 [m] (素子0表面=0)
    w: dict                        # {"t": ndarray, "s": ndarray} ビーム半径 [m]
    op_slices: list                # PropOp ごとの (op, slice) — 3D描画との対応付け用
    element_s: list                # 各素子の経路座標 [m]
    element_w: list                # 各素子位置での (w_t, w_s) [m]
    total_length: float            # 共振器全長(幾何) [m]


class Cavity:
    def __init__(self, elements: list[Element], spacings: list[float],
                 wavelength: float = 1030e-9, name: str = "cavity"):
        self.elements = elements
        self.spacings = spacings
        self.wavelength = wavelength
        self.name = name

    # ---------------------------------------------------------------
    def validate(self) -> list[str]:
        errs = []
        n, m = len(self.elements), len(self.spacings)
        if n < 2:
            errs.append("素子は2個以上必要です")
            return errs
        if m != n - 1:
            errs.append(f"spacings の数が不正 (素子{n}個に対し{m}個, 必要は{n-1}個)")
        if not self.elements[0].is_end or not self.elements[-1].is_end:
            errs.append("先頭と末尾の素子は端面鏡 (role='end') にしてください")
        for i, el in enumerate(self.elements[1:-1], 1):
            if el.is_end:
                errs.append(f"素子{i} '{el.name}' が中間にありますが role='end' です")
        if any(d < 0 for d in self.spacings):
            errs.append("負の間隔があります")
        return errs

    # ---------------------------------------------------------------
    def forward_ops(self) -> list:
        """素子0反射直後 → 素子N-1到達直前 までの op 列(端面鏡の行列は含まない)."""
        ops: list = []
        for i in range(1, len(self.elements)):
            d = self.spacings[i - 1]
            if d > 0:
                ops.append(PropOp(d, {"t": d, "s": d}, 1.0, None))
            el = self.elements[i]
            if el.path_length > 0:
                ops.append(PropOp(el.path_length,
                                  {p: el.reduced_length(p) for p in PLANES},
                                  getattr(el, "n", 1.0), el))
            elif i < len(self.elements) - 1:
                ops.append(MatOp(el, i))
        return ops

    def round_trip_matrix(self, plane: str) -> np.ndarray:
        fwd = np.eye(2)
        for op in self.forward_ops():
            fwd = self._op_matrix(op, plane) @ fwd
        back = np.eye(2)
        for op in reversed(self.forward_ops()):
            back = self._op_matrix(op, plane) @ back
        m_far = self.elements[-1].rt_matrix(plane)
        m_near = self.elements[0].rt_matrix(plane)
        return m_near @ back @ m_far @ fwd

    @staticmethod
    def _op_matrix(op, plane: str) -> np.ndarray:
        if isinstance(op, PropOp):
            return np.array([[1.0, op.red_len[plane]], [0.0, 1.0]])
        return op.element.rt_matrix(plane)

    # ---------------------------------------------------------------
    def compute(self, max_step: float = 1e-3) -> CaveResult:
        """固有モードを解き, 経路に沿ったコースティック w(s) を計算する."""
        m_rt = {p: self.round_trip_matrix(p) for p in PLANES}
        mval = {p: beam.stability_parameter(m_rt[p]) for p in PLANES}
        stable = {p: abs(mval[p]) < 1.0 for p in PLANES}
        qinv0 = {p: beam.eigen_qinv(m_rt[p]) for p in PLANES}

        ops = self.forward_ops()
        s_list, w_list = [0.0], {p: [beam.w_from_qinv(qinv0[p], self.wavelength)]
                                 for p in PLANES}
        qinv = dict(qinv0)
        op_slices = []
        element_s = [0.0]
        s = 0.0

        for op in ops:
            if isinstance(op, PropOp):
                nseg = max(8, int(np.ceil(op.geo_len / max_step)))
                start_idx = len(s_list)
                for k in range(1, nseg + 1):
                    frac = k / nseg
                    s_k = s + frac * op.geo_len
                    s_list.append(s_k)
                    for p in PLANES:
                        if qinv[p] is None:
                            w_list[p].append(float("nan"))
                        else:
                            qi = beam.propagate_qinv(
                                qinv[p],
                                np.array([[1.0, frac * op.red_len[p]], [0.0, 1.0]]))
                            w_list[p].append(beam.w_from_qinv(qi, self.wavelength))
                for p in PLANES:
                    if qinv[p] is not None:
                        qinv[p] = beam.propagate_qinv(
                            qinv[p],
                            np.array([[1.0, op.red_len[p]], [0.0, 1.0]]))
                s += op.geo_len
                op_slices.append((op, slice(start_idx - 1, len(s_list))))
                if op.owner is not None:          # 結晶の出射面
                    element_s.append(s)
            else:                                  # 点素子
                for p in PLANES:
                    if qinv[p] is not None:
                        qinv[p] = beam.propagate_qinv(
                            qinv[p], op.element.rt_matrix(p))
                element_s.append(s)
        element_s.append(s)                        # 末端鏡

        # 結晶は入射面の座標で表すよう補正: element_s には素子ごとに1点を持たせる
        elem_s_fixed, elem_w = [], []
        cursor = 0.0
        for i, el in enumerate(self.elements):
            if i > 0:
                cursor += self.spacings[i - 1]
            pos = cursor
            cursor += el.path_length
            elem_s_fixed.append(pos + el.path_length / 2 if el.path_length > 0 else pos)

        s_axis = np.asarray(s_list)
        w_arr = {p: np.asarray(w_list[p]) for p in PLANES}
        for pos in elem_s_fixed:
            idx = int(np.argmin(np.abs(s_axis - pos)))
            elem_w.append((float(w_arr["t"][idx]), float(w_arr["s"][idx])))

        return CaveResult(stable=stable, m=mval, s_axis=s_axis, w=w_arr,
                          op_slices=op_slices, element_s=elem_s_fixed,
                          element_w=elem_w, total_length=float(s))
