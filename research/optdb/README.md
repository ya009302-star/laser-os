# optdb — 光学素子・光学系データベース (研究データ)

実在の光学素子 (ミラー, OC, カーブミラー CM, GTI, SESAM, レンズ, LD) と、
それらを組んだ共振器セットアップを管理する。将来のデジタルツインの
入力源 — 「実験室の棚にある実物」をデータ化する場所。

> **状態: 枠組みのみ。** elements/ と setups/ は現在空。

## ディレクトリ

- `elements/` — 個々の光学素子 (型番・ROC・基板・コーティング・
  反射率/透過率・分散など。値には source_status と出典)
- `setups/` — 素子を組んだ共振器構成。cavsim プロジェクト JSON と
  対応づけ、どの実素子をどう配置したかを記録

## 想定スキーマ (elements/<id>.json) — ドラフト

```json
{
  "id": "thorlabs-CMxxx",
  "type": "curved_mirror",
  "roc_mm": null,
  "coating": null,
  "vendor": "(例: Thorlabs)",
  "part_number": null,
  "source_status": "unknown",
  "source": "メーカー datasheet を litdb に登録後に参照"
}
```

注: メーカー公称値も「datasheet という出典のある literature 値」として
扱い、出典 (litdb id) を必ず付ける。実測した素子特性は measured とする。
スキーマは最初の実データ登録時に確定させる。
