"""3D ビューポート.

- ビーム中心線 + 包絡線(±w_t 水平 / ±w_s 鉛直, 拡大率 w_scale)を描画
- 素子をクリックで選択, 選択素子を左ドラッグで入射軸に沿って移動
  (前側の間隔を変更. Shift+ドラッグで後側の間隔を変更)
- 空き空間のドラッグは通常のカメラ操作(回転/パン/ズーム)

シーン単位は mm.
"""
from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui

try:
    import pyqtgraph.opengl as gl
    HAS_GL = True
except Exception:                                  # OpenGL 環境がない場合
    HAS_GL = False

PICK_RADIUS_PX = 28
COLOR_BEAM = (1.00, 0.35, 0.25, 1.0)
COLOR_ENV_T = (1.00, 0.75, 0.20, 0.9)
COLOR_ENV_S = (0.35, 0.75, 1.00, 0.9)
COLOR_MIRROR = (0.65, 0.70, 0.78, 1.0)
COLOR_CRYSTAL = (0.30, 0.85, 0.55, 0.85)
COLOR_SELECTED = (1.00, 0.45, 0.10, 1.0)


def _box_mesh(sx, sy, sz):
    v = np.array([[x, y, z] for x in (-sx / 2, sx / 2)
                  for y in (-sy / 2, sy / 2) for z in (-sz / 2, sz / 2)])
    f = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5],
                  [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6],
                  [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]])
    return gl.MeshData(vertexes=v, faces=f)


if HAS_GL:

    class Viewport3D(gl.GLViewWidget):
        elementClicked = QtCore.Signal(int)
        elementDragged = QtCore.Signal(int, float, bool)  # (index, Δ[m], after側?)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setBackgroundColor("#14181f")
            self.setCameraPosition(distance=900, elevation=28, azimuth=-60)
            grid = gl.GLGridItem()
            grid.setSize(1200, 1200)
            grid.setSpacing(50, 50)
            self._grid = grid
            self.addItem(grid)
            self._poses = []
            self._selected = -1
            self._dragging = False
            self._last_pos = None

        # --- シーン構築 -------------------------------------------
        def set_scene(self, poses, caustic, selected: int = -1):
            self._poses = poses
            self._selected = selected
            for it in list(self.items):
                if it is not self._grid:
                    self.removeItem(it)

            def line(pts_m, color, width):
                if len(pts_m) < 2:
                    return
                self.addItem(gl.GLLinePlotItem(
                    pos=np.asarray(pts_m) * 1e3, color=color,
                    width=width, antialias=True, mode="line_strip"))

            line(caustic["center"], COLOR_BEAM, 2.0)
            line(caustic["env_t_plus"], COLOR_ENV_T, 1.5)
            line(caustic["env_t_minus"], COLOR_ENV_T, 1.5)
            line(caustic["env_s_plus"], COLOR_ENV_S, 1.5)
            line(caustic["env_s_minus"], COLOR_ENV_S, 1.5)

            for pose in poses:
                self._add_element_item(pose)

            center = np.mean([p.position for p in poses], axis=0) * 1e3
            self.opts["center"] = QtGui.QVector3D(*center.tolist())
            self.update()

        def _add_element_item(self, pose):
            from ..core.elements import Crystal
            el = pose.elem
            sel = (pose.index == self._selected)
            color = COLOR_SELECTED if sel else (
                COLOR_CRYSTAL if isinstance(el, Crystal) else COLOR_MIRROR)
            if isinstance(el, Crystal):
                md = _box_mesh(el.path_length * 1e3, 6.0, 6.0)
                item = gl.GLMeshItem(meshdata=md, smooth=False, color=color,
                                     shader="shaded", drawEdges=True)
                self._orient(item, np.array([1.0, 0, 0]), pose.out_dir)
            else:
                md = gl.MeshData.cylinder(rows=1, cols=40,
                                          radius=[6.35, 6.35], length=3.0)
                item = gl.GLMeshItem(meshdata=md, smooth=True, color=color,
                                     shader="shaded")
                # cylinder 軸は +z. 法線方向に向け, 反射面が position に来るよう奥へ
                self._orient(item, np.array([0.0, 0, 1.0]), -pose.normal)
            p = pose.position * 1e3
            item.translate(p[0], p[1], p[2])
            self.addItem(item)

        @staticmethod
        def _orient(item, axis_from, axis_to):
            a, b = np.asarray(axis_from, float), np.asarray(axis_to, float)
            b = b / (np.linalg.norm(b) + 1e-12)
            cross = np.cross(a, b)
            dot = float(np.clip(np.dot(a, b), -1, 1))
            ang = np.degrees(np.arccos(dot))
            if np.linalg.norm(cross) < 1e-9:
                cross = np.array([0.0, 0.0, 1.0]) if abs(a[2]) < 0.9 else np.array([0.0, 1.0, 0.0])
                if dot > 0:
                    ang = 0.0
            item.rotate(ang, *cross.tolist())

        # --- ピッキング -------------------------------------------
        def _screen_xy(self, world_m):
            try:
                m = self.projectionMatrix() * self.viewMatrix()
            except Exception:
                return None
            p = np.asarray(world_m) * 1e3
            v = m.map(QtGui.QVector4D(p[0], p[1], p[2], 1.0))
            if v.w() <= 1e-9:
                return None
            x = (v.x() / v.w() + 1) / 2 * self.width()
            y = (1 - (v.y() / v.w() + 1) / 2) * self.height()
            return np.array([x, y])

        def _pick(self, pos_px):
            best, best_d = -1, PICK_RADIUS_PX
            for pose in self._poses:
                sp = self._screen_xy(pose.position)
                if sp is None:
                    continue
                d = float(np.hypot(*(sp - pos_px)))
                if d < best_d:
                    best, best_d = pose.index, d
            return best

        # --- マウス操作 -------------------------------------------
        def mousePressEvent(self, ev):
            pos = np.array([ev.position().x(), ev.position().y()])
            if ev.button() == QtCore.Qt.LeftButton:
                idx = self._pick(pos)
                if idx >= 0:
                    self.elementClicked.emit(idx)
                    if idx >= 1:                    # 素子0は原点固定の基準
                        self._dragging = True
                        self._last_pos = pos
                        ev.accept()
                        return
            super().mousePressEvent(ev)

        def mouseMoveEvent(self, ev):
            if self._dragging and self._selected >= 1:
                pos = np.array([ev.position().x(), ev.position().y()])
                pose = next((p for p in self._poses
                             if p.index == self._selected), None)
                if pose is not None:
                    p0 = self._screen_xy(pose.position)
                    p1 = self._screen_xy(pose.position + pose.in_dir * 0.010)
                    if p0 is not None and p1 is not None:
                        ax = p1 - p0                 # 10mm あたりの画面ベクトル
                        norm2 = float(ax @ ax)
                        if norm2 > 1e-9:
                            delta_mm = float((pos - self._last_pos) @ ax) / norm2 * 10.0
                            after = bool(ev.modifiers() & QtCore.Qt.ShiftModifier)
                            self.elementDragged.emit(
                                self._selected, delta_mm * 1e-3, after)
                self._last_pos = pos
                ev.accept()
                return
            super().mouseMoveEvent(ev)

        def mouseReleaseEvent(self, ev):
            self._dragging = False
            super().mouseReleaseEvent(ev)

else:

    from PySide6 import QtWidgets

    class Viewport3D(QtWidgets.QLabel):           # type: ignore[no-redef]
        """OpenGL が使えない環境向けのフォールバック."""
        elementClicked = QtCore.Signal(int)
        elementDragged = QtCore.Signal(int, float, bool)

        def __init__(self, parent=None):
            super().__init__("3D 表示には OpenGL 環境が必要です", parent)
            self.setAlignment(QtCore.Qt.AlignCenter)

        def set_scene(self, poses, caustic, selected=-1):
            pass
