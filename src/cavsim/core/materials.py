"""材料データベース (最小実装).

CONTRIBUTING.md 規則 3・4 に従う:
- 各エントリは source_status と出典 (source) を必須フィールドとして持つ
- source_status が 'estimated' / 'unknown' の値を計算に使うと警告を出す
- 出典のない係数を追加してはならない (推定値での穴埋め禁止)

収録材料 (v0.2):
- fused_silica : Malitson 1965 (literature)

Yb:YAG / YAG などは係数の出典 (例: Zelmon et al. 1998) をユーザーが指定した
時点で追加する。`add_material()` で実行時登録も可能。

屈折率は Sellmeier 式  n²(λ) = 1 + Σᵢ Bᵢ λ² / (λ² − Cᵢ)  (λ は µm) で表す。
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np

C_LIGHT = 299792458.0  # [m/s] SI 定義値

SOURCE_STATUSES = ("literature", "measured", "estimated", "unknown")


@dataclass(frozen=True)
class Material:
    name: str
    sellmeier_b: tuple          # (B1, B2, B3, ...)
    sellmeier_c_um2: tuple      # (C1, C2, C3, ...) [µm²]
    range_um: tuple             # 有効波長範囲 (lo, hi) [µm]
    source_status: str          # 'literature' | 'measured' | 'estimated' | 'unknown'
    source: str                 # 出典 (論文・データシート等)
    notes: str = ""

    def __post_init__(self):
        if self.source_status not in SOURCE_STATUSES:
            raise ValueError(f"source_status は {SOURCE_STATUSES} のいずれか")
        if not self.source:
            raise ValueError("source (出典) は必須です")
        if len(self.sellmeier_b) != len(self.sellmeier_c_um2):
            raise ValueError("Sellmeier 係数 B, C の数が一致しません")

    # ------------------------------------------------------------------
    def _check(self, wl_um: float):
        if self.source_status in ("estimated", "unknown"):
            warnings.warn(
                f"材料 '{self.name}' の source_status は "
                f"'{self.source_status}' です (出典未確定の値を使用中)",
                stacklevel=3)
        lo, hi = self.range_um
        if not (lo <= wl_um <= hi):
            warnings.warn(
                f"材料 '{self.name}' の有効範囲 {lo}–{hi} µm 外の波長 "
                f"{wl_um:.4g} µm で評価しています", stacklevel=3)

    def n(self, wavelength: float) -> float:
        """屈折率 n(λ). wavelength は SI [m]."""
        wl_um = wavelength * 1e6
        self._check(wl_um)
        return float(self._n_um(wl_um))

    def _n_um(self, wl_um) -> np.ndarray:
        l2 = np.asarray(wl_um, dtype=float) ** 2
        n2 = 1.0 + sum(b * l2 / (l2 - c)
                       for b, c in zip(self.sellmeier_b, self.sellmeier_c_um2))
        return np.sqrt(n2)

    # --- 分散 ----------------------------------------------------------
    def _dn_dlam(self, wl_um: float, order: int, h_um: float = 2e-3) -> float:
        """dⁿn/dλⁿ [µm⁻ⁿ] (5点中心差分; 妥当性は ω 微分との照合テストで担保)."""
        f = self._n_um
        x, h = wl_um, h_um
        if order == 2:
            val = (-f(x - 2 * h) + 16 * f(x - h) - 30 * f(x)
                   + 16 * f(x + h) - f(x + 2 * h)) / (12 * h * h)
        elif order == 3:
            val = (-f(x - 2 * h) + 2 * f(x - h)
                   - 2 * f(x + h) + f(x + 2 * h)) / (2 * h**3)
        else:
            raise ValueError("order は 2 か 3")
        return float(val)

    def gvd(self, wavelength: float) -> float:
        """群速度分散 k₂ = (λ³/2πc²)·d²n/dλ² [s²/m]. wavelength は SI [m]."""
        wl_um = wavelength * 1e6
        self._check(wl_um)
        d2 = self._dn_dlam(wl_um, 2) * 1e12          # [µm⁻²] → [m⁻²]
        return wavelength**3 / (2 * np.pi * C_LIGHT**2) * d2

    def tod_per_length(self, wavelength: float) -> float:
        """三次分散 k₃ = −(λ⁴/4π²c³)·(3·d²n/dλ² + λ·d³n/dλ³) [s³/m]."""
        wl_um = wavelength * 1e6
        self._check(wl_um)
        d2 = self._dn_dlam(wl_um, 2) * 1e12          # [m⁻²]
        d3 = self._dn_dlam(wl_um, 3) * 1e18          # [m⁻³]
        return -wavelength**4 / (4 * np.pi**2 * C_LIGHT**3) \
            * (3 * d2 + wavelength * d3)


# ----------------------------------------------------------------------
MATERIALS: dict[str, Material] = {}


def add_material(mat: Material) -> None:
    MATERIALS[mat.name] = mat


def get_material(name: str) -> Material:
    if name not in MATERIALS:
        raise KeyError(
            f"未登録の材料 '{name}'. 登録済み: {sorted(MATERIALS)}. "
            "係数と出典を指定して add_material() で登録してください "
            "(出典のない推定値の登録は禁止: CONTRIBUTING.md 規則3)")
    return MATERIALS[name]


add_material(Material(
    name="fused_silica",
    sellmeier_b=(0.6961663, 0.4079426, 0.8974794),
    sellmeier_c_um2=(0.0684043**2, 0.1162414**2, 9.896161**2),
    range_um=(0.21, 3.71),
    source_status="literature",
    source=("I. H. Malitson, 'Interspecimen comparison of the refractive "
            "index of fused silica,' J. Opt. Soc. Am. 55, 1205-1209 (1965), "
            "20 degC"),
))
