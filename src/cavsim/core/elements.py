"""光学素子の定義.

素子は2種類に大別される:
- 点素子 (ミラー, レンズ): rt_matrix(plane) が作用する
- 体積素子 (結晶/ガラス板): path_length と reduced_length(plane) で伝搬として扱う

新しい素子を追加する場合: クラスを定義し ELEMENT_TYPES に登録するだけでよい.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from . import matrices as mat


@dataclass
class Element:
    name: str = ""
    type_id = "base"

    # --- 光学的性質 -------------------------------------------------
    def rt_matrix(self, plane: str) -> np.ndarray:
        """点素子として作用する ABCD 行列(体積素子は単位行列)."""
        return np.eye(2)

    @property
    def path_length(self) -> float:
        """ビームが素子内部を進む幾何長 [m](点素子は 0)."""
        return 0.0

    def reduced_length(self, plane: str) -> float:
        """縮約伝搬長 [m](点素子は 0)."""
        return 0.0

    @property
    def is_end(self) -> bool:
        return False

    @property
    def deflects(self) -> bool:
        """折返しミラーとしてビーム方向を変えるか."""
        return False

    # --- 直列化 -----------------------------------------------------
    def to_dict(self) -> dict:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        raise NotImplementedError


@dataclass
class FlatMirror(Element):
    """平面鏡. role='end' で端面鏡(SESAM/平面OCなど), 'fold' で折返し."""
    aoi_deg: float = 0.0
    turn: int = 1            # 折返し方向 (+1: 左折 / -1: 右折, 水平面内)
    role: str = "end"        # 'end' or 'fold'
    gdd_fs2: float = 0.0     # 1反射あたりの GDD [fs²] (コーティング値, ユーザー入力)
    tod_fs3: float = 0.0     # 1反射あたりの TOD [fs³]
    type_id = "flat_mirror"

    def rt_matrix(self, plane):
        return mat.flat_mirror()

    @property
    def is_end(self):
        return self.role == "end"

    @property
    def deflects(self):
        return self.role == "fold"

    def to_dict(self):
        return {"type": self.type_id, "name": self.name, "aoi_deg": self.aoi_deg,
                "turn": self.turn, "role": self.role,
                "gdd_fs2": self.gdd_fs2, "tod_fs3": self.tod_fs3}

    @classmethod
    def from_dict(cls, d):
        return cls(name=d.get("name", ""), aoi_deg=d.get("aoi_deg", 0.0),
                   turn=d.get("turn", 1), role=d.get("role", "end"),
                   gdd_fs2=d.get("gdd_fs2", 0.0), tod_fs3=d.get("tod_fs3", 0.0))


@dataclass
class CurvedMirror(Element):
    """球面鏡. roc>0 が凹面. 斜入射時は t/s で実効焦点距離が異なる."""
    roc: float = 0.1         # [m]
    aoi_deg: float = 0.0
    turn: int = 1
    role: str = "fold"
    gdd_fs2: float = 0.0     # 1反射あたりの GDD [fs²]
    tod_fs3: float = 0.0     # 1反射あたりの TOD [fs³]
    type_id = "curved_mirror"

    def rt_matrix(self, plane):
        return mat.curved_mirror(self.roc, np.deg2rad(self.aoi_deg), plane)

    @property
    def is_end(self):
        return self.role == "end"

    @property
    def deflects(self):
        return self.role == "fold"

    def to_dict(self):
        return {"type": self.type_id, "name": self.name, "roc_mm": self.roc * 1e3,
                "aoi_deg": self.aoi_deg, "turn": self.turn, "role": self.role,
                "gdd_fs2": self.gdd_fs2, "tod_fs3": self.tod_fs3}

    @classmethod
    def from_dict(cls, d):
        return cls(name=d.get("name", ""), roc=d["roc_mm"] * 1e-3,
                   aoi_deg=d.get("aoi_deg", 0.0), turn=d.get("turn", 1),
                   role=d.get("role", "fold"),
                   gdd_fs2=d.get("gdd_fs2", 0.0), tod_fs3=d.get("tod_fs3", 0.0))


@dataclass
class ThinLens(Element):
    f: float = 0.1           # [m]
    gdd_fs2: float = 0.0     # 1通過あたりの GDD [fs²] (基板等, ユーザー入力)
    tod_fs3: float = 0.0     # 1通過あたりの TOD [fs³]
    type_id = "thin_lens"

    def rt_matrix(self, plane):
        return mat.thin_lens(self.f)

    def to_dict(self):
        return {"type": self.type_id, "name": self.name, "f_mm": self.f * 1e3,
                "gdd_fs2": self.gdd_fs2, "tod_fs3": self.tod_fs3}

    @classmethod
    def from_dict(cls, d):
        return cls(name=d.get("name", ""), f=d["f_mm"] * 1e-3,
                   gdd_fs2=d.get("gdd_fs2", 0.0), tod_fs3=d.get("tod_fs3", 0.0))


@dataclass
class Crystal(Element):
    """利得媒質/ガラス板. brewster=True でブリュースター入射として扱う.

    length はビームが媒質内を進む幾何光路長 ℓ [m].
    """
    length: float = 3e-3     # [m]
    n: float = 1.82          # Yb:YAG @1030nm ≈ 1.82
    brewster: bool = True
    tilt: int = 1            # ブリュースター傾きの向き (+1/-1, 横変位の符号)
    thermal_f: float = 0.0   # 熱レンズ焦点距離 [m] (0=無効, ユーザー入力値)
    material: str = ""       # 材料DB参照名 (分散記帳に使用; ABCD の n は変えない)
    gdd_fs2: float = 0.0     # 1通過あたりの追加 GDD [fs²] (材料分とは加算)
    tod_fs3: float = 0.0     # 1通過あたりの追加 TOD [fs³]
    type_id = "crystal"

    @property
    def path_length(self):
        return self.length

    def reduced_length(self, plane):
        if self.brewster:
            return mat.reduced_length_brewster(self.length, self.n, plane)
        return mat.reduced_length_normal(self.length, self.n)

    def to_dict(self):
        return {"type": self.type_id, "name": self.name, "length_mm": self.length * 1e3,
                "n": self.n, "brewster": self.brewster, "tilt": self.tilt,
                "thermal_f_mm": self.thermal_f * 1e3,
                "material": self.material,
                "gdd_fs2": self.gdd_fs2, "tod_fs3": self.tod_fs3}

    @classmethod
    def from_dict(cls, d):
        return cls(name=d.get("name", ""), length=d["length_mm"] * 1e-3,
                   n=d.get("n", 1.82), brewster=d.get("brewster", True),
                   tilt=d.get("tilt", 1),
                   thermal_f=d.get("thermal_f_mm", 0.0) * 1e-3,
                   material=d.get("material", ""),
                   gdd_fs2=d.get("gdd_fs2", 0.0), tod_fs3=d.get("tod_fs3", 0.0))


ELEMENT_TYPES = {c.type_id: c for c in (FlatMirror, CurvedMirror, ThinLens, Crystal)}


def element_from_dict(d: dict) -> Element:
    return ELEMENT_TYPES[d["type"]].from_dict(d)
