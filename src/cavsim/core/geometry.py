"""共振器の 3D レイアウト計算.

ビーム経路は水平面(xy)内で折り返すものとする(接線面 = 水平面).
折返しミラーは入射角 aoi により偏向角 δ = π - 2*aoi だけ向きを変える.
turn=+1 で左折, -1 で右折.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from .cavity import Cavity, PropOp

UP = np.array([0.0, 0.0, 1.0])


@dataclass
class ElementPose:
    index: int
    position: np.ndarray       # 素子中心 [m]
    in_dir: np.ndarray         # 入射方向(単位ベクトル)
    out_dir: np.ndarray        # 出射方向
    normal: np.ndarray         # 反射面法線(ミラー) or ビーム方向(透過素子)
    elem: object = None        # 対応する Element への参照


@dataclass
class PathSegment:
    start: np.ndarray
    direction: np.ndarray      # 単位ベクトル
    length: float
    n: float                   # 表示用屈折率(>1 なら結晶内)


def _rot_z(v: np.ndarray, angle: float) -> np.ndarray:
    c, s = np.cos(angle), np.sin(angle)
    return np.array([c * v[0] - s * v[1], s * v[0] + c * v[1], v[2]])


def build_layout(cav: Cavity):
    """(poses, segments) を返す. segments は Cavity.forward_ops() の PropOp と同順."""
    pos = np.zeros(3)
    direction = np.array([1.0, 0.0, 0.0])
    poses: list[ElementPose] = []
    segments: list[PathSegment] = []

    # 素子0(端面鏡)
    el0 = cav.elements[0]
    poses.append(ElementPose(0, pos.copy(), -direction, direction, -direction, el0))

    for i in range(1, len(cav.elements)):
        d = cav.spacings[i - 1]
        if d > 0:
            segments.append(PathSegment(pos.copy(), direction.copy(), d, 1.0))
            pos = pos + direction * d
        el = cav.elements[i]
        in_dir = direction.copy()

        if el.path_length > 0:                       # 結晶: 直進(変位は v0.2 で対応)
            center = pos + direction * (el.path_length / 2)
            segments.append(PathSegment(pos.copy(), direction.copy(),
                                        el.path_length, getattr(el, "n", 1.0)))
            pos = pos + direction * el.path_length
            poses.append(ElementPose(i, center, in_dir, direction.copy(),
                                     direction.copy(), el))
            continue

        if el.deflects:                              # 折返しミラー
            aoi = np.deg2rad(getattr(el, "aoi_deg", 0.0))
            turn = getattr(el, "turn", 1)
            out_dir = _rot_z(in_dir, turn * (np.pi - 2.0 * aoi))
            normal = out_dir - in_dir
            nrm = np.linalg.norm(normal)
            normal = normal / nrm if nrm > 1e-12 else -in_dir
            poses.append(ElementPose(i, pos.copy(), in_dir, out_dir, normal, el))
            direction = out_dir
        else:                                        # 端面鏡 / レンズ
            normal = -in_dir if el.is_end else in_dir
            poses.append(ElementPose(i, pos.copy(), in_dir, in_dir.copy(), normal, el))

    return poses, segments


def caustic_points(cav: Cavity, result, w_scale: float = 200.0):
    """3D 描画用の点列を返す.

    Returns: dict
      center: (N,3) ビーム中心線
      env_t_plus/minus: 接線面の包絡線 (±w_t * w_scale)
      env_s_plus/minus: サジタル面の包絡線 (±w_s * w_scale)
    """
    _, segments = build_layout(cav)
    centers, et_p, et_m, es_p, es_m = [], [], [], [], []

    for (op, sl), seg in zip(result.op_slices, segments):
        s_local = result.s_axis[sl] - result.s_axis[sl][0]
        w_t = result.w["t"][sl] * w_scale
        w_s = result.w["s"][sl] * w_scale
        side = np.cross(seg.direction, UP)
        nn = np.linalg.norm(side)
        side = side / nn if nn > 1e-12 else np.array([0.0, 1.0, 0.0])
        pts = seg.start[None, :] + seg.direction[None, :] * s_local[:, None]
        centers.append(pts)
        et_p.append(pts + side[None, :] * w_t[:, None])
        et_m.append(pts - side[None, :] * w_t[:, None])
        es_p.append(pts + UP[None, :] * w_s[:, None])
        es_m.append(pts - UP[None, :] * w_s[:, None])

    cat = lambda lst: np.vstack(lst) if lst else np.zeros((0, 3))
    return {"center": cat(centers), "env_t_plus": cat(et_p), "env_t_minus": cat(et_m),
            "env_s_plus": cat(es_p), "env_s_minus": cat(es_m)}
