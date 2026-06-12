# Changelog

## v0.2.1 (2026-06-13)

cavsim 解析機能の拡張 (実測待ち期間の改善。ROADMAP v0.3 は未着手のまま)。
JSON スキーマ・既存挙動に変更なし。

- ミスアライメント感度解析 (`analysis/sensitivity.py`): 拡張 3×3 ABCD に
  よるミラー傾き/デセンタ応答。2鏡共振器の幾何学的厳密解と機械精度で一致
- 2D スタビリティマップ (`scan_spacing_2d`) + GUI タブ (クリックで間隔設定)
- 安定許容差 (`stability_margins`): 各間隔の不安定化までの距離 (二分法)
- 出力ビーム伝搬と z–w コースティックフィット (`analysis/beamfit.py`):
  平面端面鏡の外側の w(z)・ウエスト・M² フィット
- GUI「解析」メニューに感度/許容差/出力ビームのレポートを追加
- テスト 37 → 58 件 (全合格)。VALIDATION.md の表を v0.2 分も含めて整備

## v0.2.0 (2026-06-12)

物理拡張 + 検証強化 (ROADMAP v0.2)。既存 JSON (schema_version=1) は
そのまま読込可能 (追加フィールドはすべて省略可)。

- 非点収差補償角: 閉形式 cosθ=√(1+M²)−M (M=ΔL/(kR)) と、厳密往復行列に
  よる数値最適化 (`analysis/astigmatism.py`)。GUI「解析」メニューから
  計算・適用可能
- ブリュースター結晶のビーム横変位を 3D 配置にモデル化
  (横変位 ℓ(n²−1)/(n²+1)、`Crystal.tilt` で向き指定)。ABCD は不変
- 熱レンズ単純モデル: `Crystal.thermal_f` (ユーザー入力、結晶中央の
  薄レンズ、t/s 等方)
- 分散記帳: 全素子に GDD/TOD (反射/通過あたり、ユーザー入力)、
  `analysis/dispersion.py` で往復集計レポート
- 材料DB最小実装 (`core/materials.py`): source_status/出典必須、
  estimated/unknown 使用時に警告。収録は fused_silica (Malitson 1965)
  のみ。Yb:YAG 等は出典提供後に追加
- 予測-実測比較ワークフロー (`analysis/comparison.py` +
  `examples/measurements_template.json`)。VERIFIED-EXPERIMENT への
  昇格手順を VALIDATION.md に明文化
- テスト 9 → 37 件 (全合格)

## v0.1.0 (2026-06-12)

初版。

- コア物理エンジン: 縮約規約ABCD行列 (t/s面独立)、斜入射凹面鏡、
  ブリュースタースラブ、固有qパラメータ、安定性判定、w(s)分布
- 3D配置エンジン: Z-fold折返しレイアウト、コースティック点列生成
- GUI (PySide6 + pyqtgraph): 3Dビューポート (ビーム包絡線、素子選択、
  ドラッグで間隔変更)、インスペクタ、コースティックプロット、間隔スキャン
- JSONプロジェクト保存/読込 (schema_version=1)
- プリセット: Z-fold Yb:YAG (d=50.55mm, 安定)、直線共振器
- pytest 9件 (解析解照合含む)
- リポジトリ整備: laser-os リポジトリとして公開準備
  (CONTRIBUTING.md, docs/VALIDATION.md, docs/ROADMAP.md を追加)
