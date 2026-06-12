"""出力ビームの伝搬予測と z–w コースティックフィット.

(1) output_beam(): 共振器固有モードを端面鏡 (平面) の外へ透過させ、
    外部での w(z) ・ウエスト位置/径・レイリー長を返す。
    基板の屈折・レンズ効果は無視する (薄い平面 OC 近似)。
    曲面端面鏡の透過は基板依存のレンズ効果が大きいため対象外 (ValueError)。

(2) fit_caustic(): 実測 (z, w) 点列を w²(z) = a z² + b z + c に最小二乗
    フィットし、ウエスト w0・位置 z0・発散 θ・M² を推定する。
        z0 = −b/2a,  w0² = c − b²/4a,  θ = √a,  M² = π w0 θ / λ
    将来の実測照合 (VALIDATION.md §2) で、共振器外の複数点測定から
    OC 面の w を逆算する用途を想定 (実測値はリポジトリ外で管理: 規則7)。
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..core import beam
from ..core.cavity import Cavity
from ..core.elements import FlatMirror

PLANES = ("t", "s")


@dataclass
class OutputBeam:
    """端面鏡の外側 z≥0 (鏡面=0, 外向き正) でのビーム (片面分)."""
    plane: str
    w_at_mirror: float        # 鏡面でのビーム半径 [m]
    z_waist: float            # ウエスト位置 [m] (負値 = 鏡の内側の虚ウエスト)
    w0: float                 # ウエスト半径 [m]
    z_rayleigh: float         # レイリー長 [m]
    wavelength: float

    def w_at(self, z) -> np.ndarray:
        z = np.asarray(z, dtype=float)
        return self.w0 * np.sqrt(1.0 + ((z - self.z_waist)
                                        / self.z_rayleigh) ** 2)


def _qinv_before_element(cav: Cavity, plane: str, end_index: int) -> complex:
    """固有 q̂ を、指定端面鏡に入射する直前の面まで伝搬して返す."""
    qinv = beam.eigen_qinv(cav.round_trip_matrix(plane))
    if qinv is None:
        raise ValueError(f"{plane} 面が不安定なため固有モードがありません")
    ops = cav.forward_ops()
    n_last = len(cav.elements) - 1
    for op in ops:
        qinv = beam.propagate_qinv(qinv, Cavity._op_matrix(op, plane))
    if end_index == n_last:
        return qinv
    qinv = beam.propagate_qinv(
        qinv, cav.elements[n_last].rt_matrix(plane))
    for op in reversed(ops):
        qinv = beam.propagate_qinv(qinv, Cavity._op_matrix(op, plane))
    return qinv                                # 素子0 反射直前


def output_beam(cav: Cavity, end_index: int | None = None) -> dict:
    """端面鏡 end_index (既定: 末尾) の外側のビームを {plane: OutputBeam} で返す."""
    if end_index is None:
        end_index = len(cav.elements) - 1
    if end_index not in (0, len(cav.elements) - 1):
        raise ValueError("end_index は端面鏡 (0 または末尾) を指定してください")
    el = cav.elements[end_index]
    if not isinstance(el, FlatMirror):
        raise ValueError(
            "曲面端面鏡の透過は基板依存のレンズ効果があるため未対応です "
            "(平面端面鏡のみ)")
    out = {}
    for plane in PLANES:
        qinv = _qinv_before_element(cav, plane, end_index)
        q = 1.0 / qinv                          # 透過: q̂ は連続 (平面・薄基板)
        z_waist = -q.real
        z_r = q.imag
        if z_r <= 0:
            raise ValueError("固有モードが無効です (Im q ≤ 0)")
        w0 = float(np.sqrt(cav.wavelength * z_r / np.pi))
        ob = OutputBeam(plane=plane,
                        w_at_mirror=beam.w_from_qinv(qinv, cav.wavelength),
                        z_waist=float(z_waist), w0=w0,
                        z_rayleigh=float(z_r), wavelength=cav.wavelength)
        out[plane] = ob
    return out


def output_beam_text(cav: Cavity, end_index: int | None = None) -> str:
    obs = output_beam(cav, end_index)
    name = cav.elements[len(cav.elements) - 1 if end_index is None
                        else end_index].name
    lines = [f"出力ビーム ({name} の外側, 鏡面=0, 基板無視)",
             f"{'面':>3}{'w@鏡面[µm]':>13}{'ウエスト位置[mm]':>17}"
             f"{'w0[µm]':>10}{'zR[mm]':>10}{'w@+500mm[µm]':>14}"]
    for p in PLANES:
        ob = obs[p]
        lines.append(f"{p:>3}{ob.w_at_mirror*1e6:>13.1f}"
                     f"{ob.z_waist*1e3:>17.1f}{ob.w0*1e6:>10.1f}"
                     f"{ob.z_rayleigh*1e3:>10.1f}"
                     f"{float(ob.w_at(0.5))*1e6:>14.1f}")
    lines.append("ウエスト位置が負の場合は鏡の内側にある虚ウエスト")
    return "\n".join(lines)


@dataclass
class CausticFit:
    w0: float                 # [m]
    z0: float                 # ウエスト位置 [m]
    theta: float              # 遠視野半角 (w 基準) [rad]
    m2: float                 # M² 推定値
    rms_residual: float       # w の残差 RMS [m]


def fit_caustic(z, w, wavelength: float) -> CausticFit:
    """測定点 (z, w) を双曲線コースティックに最小二乗フィットする.

    z, w は SI [m]。点数 3 以上、z に広がりがあること。
    """
    z = np.asarray(z, dtype=float)
    w = np.asarray(w, dtype=float)
    if z.size < 3:
        raise ValueError("フィットには 3 点以上が必要です")
    if np.ptp(z) <= 0:
        raise ValueError("z に広がりがありません")
    a, b, c = np.polyfit(z, w ** 2, 2)
    if a <= 0:
        raise ValueError("フィット失敗: 発散項 a≤0 (データを確認してください)")
    w0_sq = c - b * b / (4 * a)
    if w0_sq <= 0:
        raise ValueError("フィット失敗: w0² ≤ 0 (データを確認してください)")
    z0 = -b / (2 * a)
    w0 = float(np.sqrt(w0_sq))
    theta = float(np.sqrt(a))
    m2 = float(np.pi * w0 * theta / wavelength)
    resid = float(np.sqrt(np.mean(
        (np.sqrt(np.polyval([a, b, c], z)) - w) ** 2)))
    return CausticFit(w0=w0, z0=float(z0), theta=theta, m2=m2,
                      rms_residual=resid)
