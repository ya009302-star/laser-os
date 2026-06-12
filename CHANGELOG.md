# Changelog

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
