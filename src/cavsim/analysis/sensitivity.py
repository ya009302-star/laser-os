"""ミスアライメント感度解析 (拡張 3×3 ABCD).

光線ベクトルを (x, n·u, 1) に拡張し、素子の微小な傾き/デセンタを
角度キック F として第3列に載せる (第一次近似):

    傾き α [rad]      : 反射ごとに Δ(n·u) = +2α   (ミラーのみ)
    デセンタ δ [m]    : Δ(n·u) = −C·δ  (凹面鏡: +2δ/R_eff, レンズ: +δ/f)

往復行列 M₃ の固定点 v = (I₂ − A₂)⁻¹·s (A₂: 左上2×2, s: 第3列上2成分) が
摂動後の光軸の基準面でのシフトであり、これを片道伝搬して各素子位置での
軸シフト Δx・軸傾き Δu を得る。

符号規約の検証 (tests/test_sensitivity.py):
平面+凹面の2鏡共振器で、平面鏡傾き α → Δx(平面鏡)=(R−L)α, Δx(凹面鏡)=Rα,
Δu=α / 凹面鏡傾き β → Δx=Rβ (両鏡), Δu=0 / 凹面鏡デセンタ δ → Δx=δ, Δu=0
という幾何学的厳密解と一致する。

注意: 折返し鏡は1往復で2回反射するため、同じキックが2回加わる
(展開光学系での標準的な第一次扱い)。t/s 両面で独立に評価する。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core.cavity import Cavity, MatOp, PropOp
from ..core.elements import Crystal, CurvedMirror, FlatMirror, ThinLens

PLANES = ("t", "s")


def _aug(m2: np.ndarray, kick: float = 0.0) -> np.ndarray:
    m = np.eye(3)
    m[:2, :2] = m2
    m[1, 2] = kick
    return m


def _kick_of(el, plane: str, kind: str, amount: float) -> float:
    """単位摂動 amount に対する角度キック Δ(n·u)."""
    if kind == "tilt":
        if not isinstance(el, (FlatMirror, CurvedMirror)):
            raise ValueError("tilt はミラーにのみ適用できます")
        return 2.0 * amount
    if kind == "decenter":
        m2 = el.rt_matrix(plane)
        c = m2[1, 0]
        if abs(c) < 1e-15:
            raise ValueError("decenter は集光性のある素子 (凹面鏡/レンズ) 用です")
        return -c * amount
    raise ValueError(f"未知の摂動種別: {kind}")


@dataclass
class AxisResponse:
    """単位摂動あたりの光軸応答 (per rad または per m)."""
    element_index: int
    kind: str
    plane: str
    dx: list                  # 各素子位置での軸シフト [m / 単位摂動]
    du: list                  # 各素子位置での軸傾き [rad / 単位摂動]


def axis_response(cav: Cavity, element_index: int, kind: str = "tilt",
                  plane: str = "t") -> AxisResponse:
    """素子 element_index の単位摂動に対する光軸応答を全素子位置で返す."""
    if plane not in PLANES:
        raise ValueError("plane は 't'/'s'")
    el_p = cav.elements[element_index]
    kick = _kick_of(el_p, plane, kind, 1.0)
    ops = cav.forward_ops()

    def op_aug(op) -> np.ndarray:
        if isinstance(op, PropOp):
            return _aug(np.array([[1.0, op.red_len[plane]], [0.0, 1.0]]))
        k = kick if op.index == element_index and \
            op.element is cav.elements[op.index] else 0.0
        return _aug(op.element.rt_matrix(plane), k)

    fwd = np.eye(3)
    for op in ops:
        fwd = op_aug(op) @ fwd
    n_last = len(cav.elements) - 1
    m_far = _aug(cav.elements[n_last].rt_matrix(plane),
                 kick if element_index == n_last else 0.0)
    m_near = _aug(cav.elements[0].rt_matrix(plane),
                  kick if element_index == 0 else 0.0)
    back = np.eye(3)
    for op in reversed(ops):
        back = op_aug(op) @ back
    m3 = m_near @ back @ m_far @ fwd

    a2, s = m3[:2, :2], m3[:2, 2]
    m_stab = 0.5 * (a2[0, 0] + a2[1, 1])
    if abs(m_stab) >= 1.0:
        raise ValueError(
            f"共振器が {plane} 面で不安定 (m={m_stab:.3f}) のため、"
            "光軸シフトは物理的に意味を持ちません")
    det = np.linalg.det(np.eye(2) - a2)
    if abs(det) < 1e-12:
        raise ValueError("臨界安定 (m≈1) のため固定点が定義できません")
    v = np.linalg.solve(np.eye(2) - a2, s)

    # 片道伝搬して各素子位置で記録 (素子の行列適用前の値)
    dx, du = [float(v[0])], [float(v[1])]
    vec = np.array([v[0], v[1], 1.0])
    recorded = {0}
    for op in ops:
        idx = op.index if isinstance(op, MatOp) else \
            (cav.elements.index(op.owner) if op.owner is not None else None)
        if idx is not None and idx not in recorded:
            recorded.add(idx)
            dx.append(float(vec[0]))
            du.append(float(vec[1]))
        vec = op_aug(op) @ vec
    if n_last not in recorded:
        dx.append(float(vec[0]))
        du.append(float(vec[1]))
    return AxisResponse(element_index, kind, plane, dx, du)


@dataclass
class SensitivityRow:
    element: str
    plane: str
    dx_per_mrad: dict          # {対象素子名: µm/mrad}


def sensitivity_table(cav: Cavity, targets: list | None = None) -> list:
    """全ミラーの傾きに対する、対象素子位置でのビーム移動量 [µm/mrad].

    targets: 対象素子インデックスのリスト (None なら結晶と両端面鏡)。
    """
    if targets is None:
        targets = [i for i, el in enumerate(cav.elements)
                   if isinstance(el, Crystal)] or []
        targets = [0] + targets + [len(cav.elements) - 1]
    rows = []
    for i, el in enumerate(cav.elements):
        if not isinstance(el, (FlatMirror, CurvedMirror)):
            continue
        for plane in PLANES:
            resp = axis_response(cav, i, "tilt", plane)
            rows.append(SensitivityRow(
                element=el.name or f"#{i}", plane=plane,
                dx_per_mrad={cav.elements[t].name or f"#{t}":
                             resp.dx[t] * 1e6 * 1e-3 for t in targets}))
    return rows


def sensitivity_text(cav: Cavity, targets: list | None = None) -> str:
    rows = sensitivity_table(cav, targets)
    names = list(rows[0].dx_per_mrad.keys()) if rows else []
    head = f"{'ミラー':<10}{'面':>3}" + "".join(f"{n:>14}" for n in names)
    lines = ["ミラー傾き感度: ビーム移動量 [µm/mrad]", head]
    for r in rows:
        lines.append(f"{r.element:<10}{r.plane:>3}"
                     + "".join(f"{r.dx_per_mrad[n]:>14.1f}" for n in names))
    return "\n".join(lines)
