"""ABCD 行列(縮約規約: 光線ベクトル (x, n*u), 常に det(M)=1).

規約メモ:
- 媒質(屈折率 n)中の幾何長 L の伝搬は [[1, L/n], [0, 1]]
- この規約では複素ビームパラメータ q^ (縮約 q) が ABCD 則で変換され,
  ビーム半径は媒質によらず w^2 = -λ0 / (π * Im(1/q^)) で得られる.
詳細は docs/PHYSICS.md を参照.
"""
from __future__ import annotations

import numpy as np

PLANES = ("t", "s")  # t: 接線面(水平/折返し面), s: サジタル面(鉛直)


def free_space(length: float, n: float = 1.0) -> np.ndarray:
    """幾何長 length [m], 屈折率 n の一様媒質伝搬."""
    return np.array([[1.0, length / n], [0.0, 1.0]])


def thin_lens(f: float) -> np.ndarray:
    """焦点距離 f [m] の薄肉レンズ(両面共通)."""
    return np.array([[1.0, 0.0], [-1.0 / f, 1.0]])


def flat_mirror() -> np.ndarray:
    """平面鏡(入射角によらず単位行列)."""
    return np.eye(2)


def curved_mirror(roc: float, aoi_rad: float, plane: str) -> np.ndarray:
    """曲率半径 roc [m] (凹面: roc>0) の球面鏡, 入射角 aoi_rad [rad].

    実効曲率: 接線面 R*cosθ, サジタル面 R/cosθ.
    """
    c = np.cos(aoi_rad)
    r_eff = roc * c if plane == "t" else roc / c
    return np.array([[1.0, 0.0], [-2.0 / r_eff, 1.0]])


def reduced_length_normal(length: float, n: float) -> float:
    """垂直入射スラブ(長さ length [m], 屈折率 n)の縮約伝搬長(両面共通)."""
    return length / n


def reduced_length_brewster(length: float, n: float, plane: str) -> float:
    """ブリュースター入射スラブの縮約伝搬長.

    length はビームが媒質内を進む幾何光路長 ℓ [m].
    接線面: ℓ/n^3, サジタル面: ℓ/n  (Kogelnik 1972 と等価).
    """
    return length / n**3 if plane == "t" else length / n
