# VALIDATION — 検証状況

最終更新: 2026-06-12 (cavsim v0.1.0)

本ファイルは cavsim の物理計算がどこまで検証されているかを記録する。
**実施していない検証を記載してはならない。** 状態は以下の3段階で表す。

- `VERIFIED-ANALYTIC` : 解析解・教科書的既知解と自動テストで照合済み
- `VERIFIED-EXPERIMENT` : 実測データと照合済み
- `UNVALIDATED` : 未検証

## 1. 自動テストによる検証 (tests/test_core.py, 9件, v0.1.0 時点で全合格)

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

## 2. 実験との比較

**状態: UNVALIDATED**

実共振器 (Z-fold Yb:YAG 等) の実測モード径・安定領域との比較は未実施。
v0.2 以降で予測-実測比較モジュールとともに整備する (docs/ROADMAP.md)。

## 3. 未検証領域 (既知)

- 3D 配置 (Z-fold レイアウト座標) の幾何は論理テストのみで、
  実機描画・実寸との照合は UNVALIDATED
- ブリュースター結晶のビーム横変位は v0.1 ではモデル化していない
- 分散・熱レンズは未実装のため検証対象外

## 4. 検証の更新規則

- 新しい物理を追加したら、本ファイルに UNVALIDATED として行を追加し、
  テスト整備後に状態を更新する
- VERIFIED-EXPERIMENT に昇格させる場合は、測定条件・日付・データの
  所在を必ず記載する
