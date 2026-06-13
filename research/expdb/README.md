# expdb — 実験ログデータベース (研究データ)

実験の記録 — 発振条件・アライメント・CW/QML 状態・出力パワー・
スペクトル・オシロ観測など — を構造化して残す。予測 (cavsim) と
実測を突き合わせる土台 (compare の入力)。

> **状態: 枠組みのみ。** logs/ は現在空 (まだ発振前)。

## 入れてよいもの / いけないもの

- 入れてよい: 測定条件・設定値・観測の要約・公開可能な結果、
  リポジトリ外にある生データ (オシロ波形 csv, スペクトル, 画像) への
  参照パス
- 入れてはいけない (規則7): 測定生データそのもの (csv/画像/波形)、
  装置固有の非公開情報

## 想定ファイル名 (logs/)

```
2026-xx-xx-ybyag-alignment.json
2026-xx-xx-ybfap-first-oscillation.json
```

## 想定スキーマ — ドラフト

```json
{
  "date": "YYYY-MM-DD",
  "material": "Yb:YAG",
  "setup_ref": "optdb/setups/<id>.json",
  "cavity_ref": "examples/zfold_ybyag.json",
  "pump_power_W": null,
  "regime": "none | CW | QML | CWML",
  "output_power_mW": null,
  "spectrum_raw_path": "(リポジトリ外)",
  "scope_raw_path": "(リポジトリ外)",
  "notes": "室温・アライメント状態・観察事項",
  "operator": ""
}
```

スキーマは最初の実ログ作成時 (= 初発振時) に確定させる。
