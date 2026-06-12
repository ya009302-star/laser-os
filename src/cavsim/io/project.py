"""共振器設計の保存/読込 (JSON, schema_version 管理).

ファイル内の単位: 長さ mm, 波長 nm (人間が読み書きしやすい単位).
内部表現は SI (m).
"""
from __future__ import annotations

import json
from pathlib import Path

from ..core.cavity import Cavity
from ..core.elements import element_from_dict

SCHEMA_VERSION = 1


def cavity_to_dict(cav: Cavity) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": cav.name,
        "wavelength_nm": cav.wavelength * 1e9,
        "elements": [el.to_dict() for el in cav.elements],
        "spacings_mm": [d * 1e3 for d in cav.spacings],
    }


def cavity_from_dict(d: dict) -> Cavity:
    ver = d.get("schema_version", 1)
    if ver > SCHEMA_VERSION:
        raise ValueError(f"未対応のスキーマバージョン: {ver}")
    elements = [element_from_dict(e) for e in d["elements"]]
    spacings = [x * 1e-3 for x in d["spacings_mm"]]
    cav = Cavity(elements, spacings,
                 wavelength=d.get("wavelength_nm", 1030.0) * 1e-9,
                 name=d.get("name", "cavity"))
    errs = cav.validate()
    if errs:
        raise ValueError("不正な共振器定義: " + "; ".join(errs))
    return cav


def save(cav: Cavity, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(cavity_to_dict(cav), ensure_ascii=False, indent=2),
        encoding="utf-8")


def load(path: str | Path) -> Cavity:
    return cavity_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
