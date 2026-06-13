# litdb — 文献データベース

論文・データシート・技術資料の**書誌情報と出典管理**を行う。
研究で使う数値の出どころを litdb までたどれる状態にすることが目的
(matdb/optdb の各値は、ここに登録した文献を source として参照する)。

> **状態: 枠組みのみ。** sources/ は現在空。

## 入れてよいもの / いけないもの

- 入れてよい: DOI・タイトル・著者・年・出版元、リポジトリ外 PDF への
  参照パス、その文献から抽出した値の要約
- 入れてはいけない (規則7): 論文 PDF そのもの、有償資料の本文

## 想定スキーマ (sources/<id>.json) — ドラフト

```json
{
  "id": "malitson1965",
  "title": "Interspecimen comparison of the refractive index of fused silica",
  "authors": ["I. H. Malitson"],
  "year": 1965,
  "doi": "10.1364/JOSA.55.001205",
  "venue": "J. Opt. Soc. Am. 55, 1205-1209",
  "pdf_path": "(リポジトリ外。例: ~/laser-research-data/papers/malitson1965.pdf)",
  "extracted": "fused silica Sellmeier 係数 (20 degC)"
}
```

注: スキーマは確定仕様ではない。最初の実データ登録時に確定させる。
