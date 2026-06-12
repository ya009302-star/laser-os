"""ガウシアンビームの複素パラメータ q^(縮約 q)の操作.

縮約規約では 1/q^ = n/R - i*λ0/(π w^2) であり,
ビーム半径は媒質によらず w = sqrt(-λ0 / (π Im(1/q^))) で得られる.
"""
from __future__ import annotations

import numpy as np


def eigen_qinv(m_rt: np.ndarray) -> complex | None:
    """往復行列 m_rt の固有モード 1/q^ を返す. 不安定なら None.

    1/q^ = (D-A)/(2B) - i*sqrt(1-m^2)/|B|,  m=(A+D)/2 (Im<0 となる枝を選択)
    """
    a, b, c, d = m_rt.ravel()
    m = 0.5 * (a + d)
    if abs(m) >= 1.0 or abs(b) < 1e-15:
        return None
    return complex((d - a) / (2.0 * b), -np.sqrt(1.0 - m * m) / abs(b))


def stability_parameter(m_rt: np.ndarray) -> float:
    """安定性パラメータ m=(A+D)/2. |m|<1 で安定."""
    return 0.5 * (m_rt[0, 0] + m_rt[1, 1])


def w_from_qinv(qinv: complex | None, wavelength: float) -> float:
    """1/q^ からビーム半径 w [m] を計算. 無効なら NaN."""
    if qinv is None or qinv.imag >= 0:
        return float("nan")
    return float(np.sqrt(-wavelength / (np.pi * qinv.imag)))


def propagate_qinv(qinv: complex, m: np.ndarray) -> complex:
    """ABCD 行列 m で 1/q^ を変換."""
    a, b, c, d = m.ravel()
    q = 1.0 / qinv
    return 1.0 / ((a * q + b) / (c * q + d))
