# laser-os — Laser Research OS

固体超短パルスレーザー研究のための統合研究ソフトウェアプロジェクト。
共振器設計・シミュレーション・検証・実験記録・文書化を、長期的に管理可能な
単一リポジトリとして開発する。

**現在の実装モジュール: `cavsim` v0.2** (レーザー共振器シミュレータ)

将来モジュール候補 (未実装、`docs/ROADMAP.md` 参照):
材料データベース / 実験ログ管理 / 分散・GDDトラッカー /
予測-実測比較 / レーザー加工解析 / FDTD系シミュレーション支援

---

## cavsim — レーザー共振器設計シミュレータ

ABCD行列法によるレーザー共振器の安定性・モード径計算と、3Dビューポートでの
インタラクティブな共振器設計を行うPCアプリケーション。
Z-fold型フェムト秒固体レーザー(斜入射凹面鏡 + ブリュースター結晶)の
非点収差を接線面(t)/サジタル面(s)で別々に扱える。

### 必要環境

- Python 3.10+ (開発・テストは 3.12 で実施)
- 依存: numpy, PySide6-Essentials, pyqtgraph, PyOpenGL (pip install で自動導入)

### インストールと GUI 起動

```bash
git clone https://github.com/<your-name>/laser-os.git
cd laser-os
pip install -e .
cavsim        # GUI起動
```

### コアエンジンのみの利用 (GUI不要)

コア物理 (`cavsim.core`, `cavsim.analysis`, `cavsim.io`) は numpy のみに依存し、
GUIライブラリ無しのヘッドレス環境で動作する。

```python
from cavsim.presets import zfold_ybyag
res = zfold_ybyag().compute()
print(res.m)          # 安定性パラメータ {"t": ..., "s": ...} (|m|<1で安定)
print(res.element_w)  # 各素子位置のビーム半径 (w_t, w_s) [m]
```

### テスト

```bash
python -m pytest tests/ -q
```

コア物理 9 件。解析解との照合 (平凹共振器ウエスト、g1g2安定性、
ブリュースター縮約長比、垂直入射結晶の等価空気共振器など) を含む。
検証状況の詳細は `docs/VALIDATION.md` を参照。

### 物理モデル (v0.1)

- ABCD行列エンジン: 接線面/サジタル面の独立計算、縮約規約 (det=1)
- 斜入射凹面鏡: R_eff = R·cosθ (接線面) / R/cosθ (サジタル面)
- ブリュースタースラブ: 縮約長 ℓ/n³ (接線面) / ℓ/n (サジタル面)
- 固有qパラメータ → 安定性判定・共振器内ビーム径分布 w(s)
- 3D配置: Z-fold折返しレイアウト、コースティック点列生成
- 間隔スキャン: 安定領域とビーム径の掃引
- JSONプロジェクト保存/読込 (schema_version=1)、プリセット
  (Z-fold Yb:YAG, 直線共振器)

物理規約の詳細は `docs/PHYSICS.md` を参照。

### v0.2 で追加された機能

- 非点収差補償角の計算 (閉形式 + 厳密行列の数値最適化、GUI「解析」メニュー)
- ブリュースター結晶のビーム横変位を 3D 配置に反映 (`Crystal.tilt` で向き)
- 熱レンズ単純モデル (`Crystal.thermal_f`、ユーザー入力、結晶中央薄レンズ)
- 分散記帳 (素子ごとの GDD/TOD + 材料分散、往復集計レポート)
- 材料DB最小実装 (出典必須。収録: fused_silica / Malitson 1965)
- 予測-実測比較ワークフロー (`examples/measurements_template.json`)

### 制限事項 (v0.2)

- 利得・損失・パワーは扱わない (純粋に幾何光学的なモード計算)
- 熱レンズは t/s 等方の単純モデル (非対称熱レンズは将来課題)
- Yb:YAG / YAG の材料分散係数は未収録 (出典指定があり次第追加)
- 3D描画・ドラッグ操作はヘッドレス環境で論理テスト済み。実機GPU環境での
  描画確認を推奨

### 検証状況

- コア物理: 教科書的な解析解と pytest で照合済み (`docs/VALIDATION.md`)
- 実測との比較: **未実施 (UNVALIDATED)**。実験値との照合は今後の課題

### 単位の規約

- 内部計算: SI (m)。JSON/GUI: 長さ mm、波長 nm
- 角度: 入射角は度 (GUI)、内部ラジアン

---

## リポジトリ構成

```
src/cavsim/
  core/       物理エンジン (行列、素子、ビーム、共振器、3D配置)
  analysis/   スキャン解析
  io/         プロジェクト保存/読込 (JSON)
  gui/        PySide6 GUI
  presets.py  プリセット共振器
tests/        pytest (コア物理)
examples/     サンプルJSON
docs/         PHYSICS.md / VALIDATION.md / ROADMAP.md
```

## 開発ポリシー

開発ルール (AI支援開発の規則を含む) は `CONTRIBUTING.md` を参照。
要点: コア物理とGUIの分離 / 物理変更には必ずテスト /
物理定数・材料値の捏造禁止 / 動作中の挙動の保全 / 大規模書き換えの原則禁止。
