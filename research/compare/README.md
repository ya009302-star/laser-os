# compare — 予測-実測比較・次実験判断 (研究データ)

cavsim の予測と expdb の実測を突き合わせ、**差分の解釈と次の一手**を
記録する。laser-os のデジタルツイン構想で最も中核に近い層 — 単に
計算するのではなく、「なぜそうなったか」「次に何を試すか」を残す。

> **状態: 枠組みのみ。** decision_support/ は現在空。

## なぜ compare という名前か

`cavsim.analysis` (計算コード) と区別するため。compare は研究記録であり、
計算ロジックではない。比較に使う計算 (M² フィット等) は cavsim 側にある。

## decision_support/ に残すもの

設計・実験の判断記録。例えば発振前後で問うべきこと:

- なぜ発振しないか (損失過多 / アライメント / ポンプ不足 / 安定領域外)
- QML の原因候補は何か (E_p² > E_sat,L·E_sat,A·ΔR の評価など)
- 往復 GDD は過多か (dispersion 記帳との照合)
- SESAM / 結晶上のビーム径は危険でないか (cavsim の element_w と照合)
- 次に何を変えるべきか (間隔 / OC / 折返し角 / ポンプ)

## 想定スキーマ (decision_support/<id>.json) — ドラフト

```json
{
  "date": "YYYY-MM-DD",
  "question": "first oscillation でQMLが出る原因は？",
  "prediction_ref": "cavsim 計算 (どのプロジェクト/設定か)",
  "measurement_ref": "expdb/logs/<id>.json",
  "observed_gap": "予測と実測の差の記述",
  "hypotheses": ["候補1", "候補2"],
  "next_action": "次に試すこと",
  "status": "open | resolved"
}
```

注: ここは「正解」を書く場所ではなく、思考と判断の履歴を残す場所。
未解決の問いは status=open のまま残してよい。スキーマは最初の
判断記録を書くときに確定させる。
