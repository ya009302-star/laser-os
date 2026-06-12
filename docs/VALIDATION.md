# VALIDATION — 検証状況

最終更新: 2026-06-13 (cavsim v0.2.1)

本ファイルは cavsim の物理計算がどこまで検証されているかを記録する。
**実施していない検証を記載してはならない。** 状態は以下の3段階で表す。

- `VERIFIED-ANALYTIC` : 解析解・教科書的既知解と自動テストで照合済み
- `VERIFIED-EXPERIMENT` : 実測データと照合済み
- `UNVALIDATED` : 未検証

## 1. 自動テストによる検証 (v0.2.1: tests/ 全58件合格)

| 項目 | テスト | 状態 |
|---|---|---|
| g1g2 安定性条件 (2鏡共振器) | `test_stability_g1g2` | VERIFIED-ANALYTIC |
| 平凹共振器のウエスト解析解 | `test_waist_plano_concave` | VERIFIED-ANALYTIC |
| 不安定共振器の検出 | `test_unstable_detection` | VERIFIED-ANALYTIC |
| 斜入射凹面鏡の t/s 実効曲率 (R·cosθ, R/cosθ) | `test_curved_mirror_astigmatism` | VERIFIED-ANALYTIC |
| ブリュースタースラブ縮約長 (ℓ/n³, ℓ/n) | `test_brewster_reduced_lengths` | VERIFIED-ANALYTIC |
| 垂直入射結晶 ↔ 等価空気路の一致 | `test_crystal_equals_reduced_path` | VERIFIED-ANALYTIC |
| 往復行列の行列式 det=1 (縮約規約) | `test_roundtrip_determinant` | VERIFIED-ANALYTIC |
| JSON 保存/読込の往復一致 | `test_project_roundtrip` | VERIFIED-ANALYTIC |
| 間隔スキャンの安定領域検出 | `test_scan_finds_stable_zone` | VERIFIED-ANALYTIC |
| 補償角: 閉形式↔厳密行列数値解の一致 | `tests/test_astigmatism.py` (4件) | VERIFIED-ANALYTIC |
| ブリュースター横変位の解析式・経路連続性 | `tests/test_geometry.py` (4件) | VERIFIED-ANALYTIC |
| 熱レンズ: 手組み等価系との厳密一致・f→∞連続性 | `tests/test_thermal.py` (6件) | VERIFIED-ANALYTIC |
| 材料分散: λ式↔ω直接微分の整合・文献アンカー (溶融石英) | `tests/test_dispersion.py` (8件) | VERIFIED-ANALYTIC |
| 実測比較ワークフローの配管 (合成測定による) | `tests/test_comparison.py` (6件) | VERIFIED-ANALYTIC |
| ミスアライメント感度: 2鏡共振器の幾何学的厳密解 | `tests/test_sensitivity.py` (9件) | VERIFIED-ANALYTIC |
| 2Dマップ↔1Dスキャン一致・許容差↔安定帯端の整合 | `tests/test_scan2d.py` (5件) | VERIFIED-ANALYTIC |
| 出力ビーム解析解・z–w フィット復元 (M² 含む) | `tests/test_beamfit.py` (7件) | VERIFIED-ANALYTIC |

## 2. 実験との比較

**状態: UNVALIDATED (比較ワークフローは v0.2 で整備済み・実測データ待ち)**

実共振器 (Z-fold Yb:YAG 等) の実測モード径・安定領域との比較は未実施。
v0.2 で `cavsim.analysis.comparison` (測定記録 JSON → 予測比較レポート) と
`examples/measurements_template.json` を整備した。配管は合成測定による
自動テストで検証済み (tests/test_comparison.py)。

VERIFIED-EXPERIMENT への昇格手順:
1. テンプレートを複製し、実測値・測定条件を記入する
2. `compare(cavity, load_measurements(path))` でレポートを生成する
3. 人間が測定の妥当性を確認した上で、本ファイルに測定日・条件・
   データ所在・結果 (平均比など) を記載して昇格させる

## 3. 未検証領域 (既知)

- 3D 配置 (Z-fold レイアウト座標) の幾何は論理テストのみで、
  実機描画・実寸との照合は UNVALIDATED
- ブリュースター結晶のビーム横変位: v0.2 で 3D 配置にモデル化
  (横変位 ℓ(n²−1)/(n²+1) の解析式照合 → VERIFIED-ANALYTIC,
  tests/test_geometry.py。実機描画・実寸照合は UNVALIDATED のまま)
- ミスアライメント感度の符号規約 (PHYSICS.md §12) と実機の調整ノブの
  向きとの対応は UNVALIDATED (大きさの比較には影響しない)
- 出力ビームは薄い平面基板近似 (基板の屈折・レンズ効果は無視): 実測照合は
  UNVALIDATED

## 4. 検証の更新規則

- 新しい物理を追加したら、本ファイルに UNVALIDATED として行を追加し、
  テスト整備後に状態を更新する
- VERIFIED-EXPERIMENT に昇格させる場合は、測定条件・日付・データの
  所在を必ず記載する
