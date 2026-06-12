"""共振器往復の分散 (GDD/TOD) 記帳.

線形共振器の 1 往復における各素子の寄与を集計する:
- 端面鏡 (素子0, N-1): 1 反射/往復
- 中間の点素子 (折返し鏡・レンズ): 2 回作用/往復
- 結晶/板: 2 通過/往復
  寄与 = 材料分散 (Crystal.material が設定されていれば k₂·ℓ, k₃·ℓ) + 追加分 (gdd_fs2 等)

空気の分散は無視する (典型的な共振器長では fs² オーダー未満)。
材料分散の係数は cavsim.core.materials の出典付きエントリのみを用いる。
"""
from __future__ import annotations

from dataclasses import dataclass

from ..core.cavity import Cavity
from ..core.elements import Crystal
from ..core.materials import get_material


@dataclass
class DispersionRow:
    name: str
    kind: str                 # 'mirror' | 'lens' | 'crystal' など
    count: int                # 1往復あたりの作用回数
    gdd_each_fs2: float       # 1作用あたり [fs²]
    tod_each_fs3: float       # 1作用あたり [fs³]
    note: str = ""

    @property
    def gdd_total_fs2(self) -> float:
        return self.count * self.gdd_each_fs2

    @property
    def tod_total_fs3(self) -> float:
        return self.count * self.tod_each_fs3


@dataclass
class DispersionReport:
    wavelength: float         # [m]
    rows: list
    gdd_total_fs2: float
    tod_total_fs3: float

    def to_text(self) -> str:
        lines = [f"往復分散 @ {self.wavelength*1e9:.1f} nm",
                 f"{'素子':<14}{'回数':>4}{'GDD/回[fs²]':>14}"
                 f"{'GDD計[fs²]':>13}{'TOD計[fs³]':>13}  備考"]
        for r in self.rows:
            lines.append(f"{r.name:<14}{r.count:>4}{r.gdd_each_fs2:>14.2f}"
                         f"{r.gdd_total_fs2:>13.2f}{r.tod_total_fs3:>13.2f}"
                         f"  {r.note}")
        lines.append(f"{'合計':<14}{'':>4}{'':>14}"
                     f"{self.gdd_total_fs2:>13.2f}{self.tod_total_fs3:>13.2f}")
        return "\n".join(lines)


def round_trip_dispersion(cav: Cavity,
                          wavelength: float | None = None) -> DispersionReport:
    """1 往復の GDD/TOD を素子別に集計する."""
    wl = cav.wavelength if wavelength is None else wavelength
    rows: list[DispersionRow] = []
    n_last = len(cav.elements) - 1

    for i, el in enumerate(cav.elements):
        count = 1 if i in (0, n_last) else 2
        if isinstance(el, Crystal):
            gdd = float(getattr(el, "gdd_fs2", 0.0))
            tod = float(getattr(el, "tod_fs3", 0.0))
            note = "追加分のみ" if not el.material else ""
            if el.material:
                mat = get_material(el.material)
                gdd += mat.gvd(wl) * el.length * 1e30          # s²→fs²
                tod += mat.tod_per_length(wl) * el.length * 1e45  # s³→fs³
                note = f"材料: {el.material} ({mat.source_status})"
            rows.append(DispersionRow(el.name or f"#{i}", "crystal", count,
                                      gdd, tod, note))
        else:
            gdd = float(getattr(el, "gdd_fs2", 0.0))
            tod = float(getattr(el, "tod_fs3", 0.0))
            kind = "mirror" if hasattr(el, "role") else "lens"
            rows.append(DispersionRow(el.name or f"#{i}", kind, count,
                                      gdd, tod))

    return DispersionReport(
        wavelength=wl, rows=rows,
        gdd_total_fs2=sum(r.gdd_total_fs2 for r in rows),
        tod_total_fs3=sum(r.tod_total_fs3 for r in rows))
