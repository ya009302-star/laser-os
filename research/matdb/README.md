# matdb — 材料データベース (研究データ)

レーザー材料 (Yb:YAG, Yb:FAP 等) の物性値を**出典つき**で管理する。
`src/cavsim/core/materials.py` の最小実装 (fused_silica, Malitson 1965) の
データ面を将来ここへ拡張する想定。

> **状態: 枠組みのみ。** materials/ は現在空。

## 厳守事項 (CONTRIBUTING 規則3・4)

- **未確認の値は登録しない。** 不明な係数は `null` のままにする。
- 各値に `source_status` (`literature` / `measured` / `estimated` /
  `unknown`) と `source` (litdb の id か出典文字列) を必須で付ける。
- `estimated` / `unknown` の値をシミュレーションに使う場合は警告する
  (materials.py の既存挙動に合わせる)。
- AI は屈折率・分散・熱光学係数などを推定値で埋めてはならない。

## 想定スキーマ (materials/<name>.json) — ドラフト

```json
{
  "name": "Yb:YAG",
  "sellmeier": null,
  "dn_dT": null,
  "thermal_conductivity": null,
  "source_status": "unknown",
  "source": "出典確定後に litdb id を記入",
  "note": "係数・出典は未確定。確定するまで null。"
}
```

Yb:YAG / Yb:FAP の具体値は**出典指定待ち**。文献が決まったら litdb に
登録し、その id を source に紐付けて値を入れる。
