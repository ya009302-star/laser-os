# SURVEY — 光学系・レーザーシミュレーターの世界地図

> **この文書の位置づけ (重要)**
> これは設計判断のための**内部調査メモ**であり、laser-os の技術仕様でも
> 検証済みの事実でもない。特に §2–§3 の競合ツール機能比較は、各ツールの
> **公開情報に基づく未検証の整理**である (AI が各ツールを実際に動かして
> 比較したものではない)。クロスチェック検証 (§4-1) を含む実機照合は
> いずれも**未実施**。実装・対外的な主張に使う前に、個々の数値・機能・
> 出典を必ず一次資料で確認すること (CONTRIBUTING 規則3)。

調査日: 2026-06-13 (Claude AI dev による web 調査 + 一般知識)。
本文中の【web確認】は当日の検索で確認した情報、【要原典照合】は AI の
一般知識であり**実装に使う前に必ず原典を確認すること** (CONTRIBUTING 規則3)。

目的: laser-os / cavsim の設計判断 (何を作り、何を作らないか、
どこと照合して検証するか) の材料にする。

---

## 1. 物理モデルの階層

レーザー・光学シミュレーションは扱う物理の解像度で階層化できる。
**上の階層ほど速く、下ほど物理が豊か**。直交する軸として「利得・熱」
「パルスダイナミクス」がある。

| 階層 | 手法 | 扱えるもの | 扱えないもの | 代表ツール |
|---|---|---|---|---|
| L1 幾何光線 | レイトレーシング | 3D配置, 収差, 照明, 迷光 | 回折, モード | Zemax, CODE V, 3DOptix, FRED |
| L2 ガウシアン | ABCD / q パラメータ | 共振器モード, 安定性, 非点収差 | 回折損失, 高次モード, 収差一般 | **cavsim**, reZonator, RP Resonator |
| L2+ 拡張 | 3×3 ABCD (misalignment), M² | 軸ずれ感度, 実ビーム | 同上 | RP Resonator, **cavsim v0.2.1** |
| L3 物理光学 | FFT/BPM 伝搬, Fox–Li 反復 | 回折, アパーチャ, 任意収差(熱レンズ収差), 高次/不安定共振器モード | 偏光の厳密扱い(拡張要), 波長スケール構造 | LASCAD(BPM), LightPipes, OSCAR, Finesse(HOM展開) |
| L4 全波 | FDTD / FEM / EME | 波長スケール構造, 導波路, PhC | マクロ共振器全体(計算量で不可能) | MEEP, Lumerical, COMSOL, CAMFR |
| 軸A 利得・熱 | レート方程式, Rigrod, FEA熱解析 | 出力パワー, 閾値, 熱レンズ, モード競合 | — | LASCAD, RP Fiber Power |
| 軸B パルス | split-step 往復伝搬 (分散+非線形+利得+可飽和吸収) | モード同期の定常パルス, 安定性, QML | — | RP ProPulse, 自作コード文化 |

**cavsim は L2/L2+ を t/s 両面で押さえた状態** (v0.2.1)。

## 2. 主要ツール各論

### reZonator 2 (OSS, C++/Qt) — 最も近い既存物
- ABCD 行列ベース。定在波/リング/単一パス系、M² 対応、要素カタログ+
  ユーザー定義行列。1D/2D スタビリティマップ (t/s 両面)、安定境界の自動
  計算、コースティック、波面曲率、非点収差込み。【web確認】
  https://github.com/orion-project/rezonator2
- 2D 回路図風レイアウトの自動描画 (3D ではない)。利得・熱・分散・パルスは
  扱わない。
- **示唆**: 機能集合が cavsim v0.2.1 とほぼ同型独立実装 → 同一共振器を
  両方で計算して突き合わせる「クロスチェック検証」の相手として最適。
  (VALIDATION に VERIFIED-CROSSCHECK 区分を追加する価値あり)

### RP Photonics スイート (商用, スクリプト型)
- **RP Resonator**: モード特性・アライメント感度・熱レンズ込み設計・
  特定安定帯狙いの最適化。【web確認】
  https://www.rp-photonics.com/resonator_design.html
- **RP ProPulse**: モード同期レーザー共振器内のパルス往復伝搬。波長依存
  損失/利得、可飽和吸収体 (fast/slow)、任意次数の分散、Kerr 非線形等を
  含み、定常状態まで自動で回す。SESAM 回復時間や往復 GDD を振って安定/
  不安定領域を出す事例あり (準ソリトンモード同期のバルクレーザー)。
  【web確認】 https://www.rp-photonics.com/rp_propulse.html
- **示唆**: ProPulse の最小核 (GDD+SPM+利得飽和+SESAM の往復 split-step)
  が、Yb フェムト秒発振器研究で cavsim に最も効く「次の物理」。

### LASCAD (商用) — 熱・利得の標準
- 熱・構造 FEA + ABCD ガウシアン + FFT split-step BPM + レーザー出力/
  ビーム品質計算 + 動的マルチモード解析 (DMA: 横モードごとの時間依存
  レート方程式; Q スイッチのパルス波形まで)。ポンプ吸収分布は ZEMAX/
  TracePro 連携。【web確認】
  http://www.hanamuraoptics.com/device/LASCAD/lascad_brochure.pdf
- FEA 結果 (温度依存屈折率分布・変形) を放物近似で ABCD に渡すか、
  近似が破れる場合は BPM へ渡す二段構え。
- **示唆**: 「FEA→放物近似→ABCD」の流れは、cavsim の thermal_f
  (ユーザー入力) の上位互換。当面はポンプパラメータからの解析式推定
  (下記 Innocenzi 式) が中間ステップとして妥当。

### レイトレース系: Zemax OpticStudio / CODE V / 3DOptix / BeamXpertDESIGNER
- 3DOptix: クラウド+GPU のレイトレーシング、ドラッグ&ドロップ 3D UI、
  実在部品 (15 ベンダー 2 万点超) の部品 DB、光学機械込み。自らを光学
  プロトタイプの「デジタルツイン」と位置づけ、「デジタルラボブック」と
  しての利用例も。【web確認】 https://www.3doptix.com/
- BeamXpertDESIGNER: ISO 11146 準拠のガウシアン/実ビームをドラッグ操作で
  リアルタイム計算。【web確認】
- **示唆**: laser-os の 3D UX と「実験室との対応」路線の先行例。
  実在部品 DB (Thorlabs 等の ROC/基板/コーティング) は optdb 構想と同型。

### OSS Python 生態系
- **LightPipes**: Fresnel 回折伝搬ツールボックス。アパーチャ・レンズ・
  ミラーを通した物理光学。教育実績多数。【web確認】
  https://opticspy.github.io/lightpipes/
- **Finesse 3 / Pykat**: 重力波干渉計コミュニティ製。周波数領域で
  高次 Hermite-Gauss モード展開、ミスマッチ/非点収差の解析。共振器の
  「フィールドで解く」文化の代表。【web確認】
- **LaserCAD** (2025, MDPI 論文): Python パラメトリックレイトレースで
  レーザービームパス+光学機械を script 記述、LightPipes 連携を計画。
  【web確認】 https://www.mdpi.com/2076-3417/15/22/11893
- Fox–Li 反復 (FFT で往復させ最低損失固有モードへ収束) は標準手法で、
  arXiv 等に実装例多数。【web確認】
- **示唆**: L3 (物理光学固有モード) を cavsim に足す場合、numpy FFT で
  自作可能 (依存追加不要)。LightPipes との突き合わせが検証に使える。

### その他
- SNLO (AS-Photonics): 非線形結晶の位相整合・変換効率計算の定番 (無償)。
  SHG/OPO に進むときの照合先。【要原典照合: 最新の配布形態】
- OSCAR (MATLAB): FFT ベース共振器フィールド計算。
- COMSOL / MEEP / Lumerical: 全波。マクロ共振器には不適、FDTD 連携は
  結晶内・微細構造の局所問題に限定するのが定石。

## 3. cavsim v0.2.1 の現在地

| 機能 | reZonator | RP Resonator | LASCAD | cavsim |
|---|---|---|---|---|
| t/s ABCD・安定性・コースティック | ◯ | ◯ | ◯ | ◯ |
| 1D/2D スタビリティマップ | ◯ | ◯ | △ | ◯ |
| 非点収差補償角の自動計算 | × | (script次第) | × | ◯ |
| ミスアライメント感度 | × | ◯ | × | ◯ |
| 安定許容差の自動算出 | △(境界計算) | (script次第) | × | ◯ |
| 分散記帳 (GDD/TOD) | × | △ | × | ◯ |
| 出力ビーム/z–w・M² フィット | △(M²伝搬) | ◯ | △ | ◯ |
| 3D 表示・操作 | × (2D図) | × | △ | ◯ |
| 利得・出力パワー | × | △ | ◯ | × |
| 熱レンズの第一原理推定 | × | △(モデル) | ◯(FEA) | × (f手入力) |
| パルス往復 (SESAM/ソリトン) | × | ×(ProPulse別売) | × | × |
| 物理光学 (回折/収差/高次モード) | × | × | ◯(BPM) | × |
| 実測比較ワークフロー・検証文化 | × | × | △(検証事例) | ◯ |

→ **L2 帯では既にトップ層と同等+独自機能 (補償角・検証文化)。
ギャップは「利得・熱の第一原理」「パルス」「物理光学」の3つ。**

## 4. laser-os への示唆 (優先順位案; 着手は ROADMAP 規則どおり指示待ち)

1. **クロスチェック検証 (コスト極小)**: Z-fold プリセットを reZonator 2 で
   再現し数値照合 → VALIDATION に第4区分 `VERIFIED-CROSSCHECK` を新設。
2. **熱レンズの解析式推定**: 端面ポンプの古典式 (Innocenzi 型,
   f_th ∝ κ w_p² / (P_heat·dn/dT))【要原典照合: Innocenzi et al., Appl.
   Phys. Lett. 56, 1831 (1990)】を thermal_f の推定補助に。Yb:YAG の
   κ, dn/dT は**出典指定待ち** (規則3)。
3. **準3準位利得・出力**: Yb:YAG/Yb:FAP は再吸収のある準3準位。レート
   方程式+Rigrod 型解析【要原典照合: Rigrod, J. Appl. Phys. 36, 2487
   (1965)】で閾値・スロープ・最適 OC を予測 → 実測パワーと照合可能に。
4. **パルス往復モデル (fs 研究の本丸)**: GDD+SPM+利得飽和+SESAM の
   split-step 往復。ソリトン面積定理とモード同期安定判定
   (Q スイッチモード同期境界 E_p² > E_sat,L·E_sat,A·ΔR)
   【要原典照合: Hönninger et al., JOSA B 16, 46 (1999)】。
   既存の分散記帳 (v0.2) と結晶内モード断面積 (v0.1) がそのまま入力になる。
5. **KLM の非線形 ABCD**【要原典照合: Magni et al., Opt. Commun. 96, 348
   (1993)】: Kerr レンズを強度依存 ABCD で。④の後が自然。
6. **物理光学固有モード (Fox–Li)**: numpy FFT で実装可能。収差つき熱
   レンズ・ハードアパーチャ・回折損失。LightPipes と照合。
7. **3D UX/部品 DB**: 3DOptix が参照例。optdb (実在ミラー/結晶カタログ)
   は ROADMAP の予約どおり。

## 5. デジタルツイン・自動化の先行研究 (長期構想の文脈)

- モード同期ファイバーレーザーの自動最適化は確立した研究分野:
  遺伝的アルゴリズムによる self-starting (Woodward & Kelleher, Sci. Rep.
  2016)、深層学習+モデル予測制御 (Baumeister, Brunton & Kutz, JOSA B
  2018)、深層強化学習 (2020–) など。【web確認】
- 商用側も「デジタルツイン」を明示的に掲げ始めている (3DOptix)。【web確認】
- laser-os の差別化軸は「出典をたどれるデータパイプライン+検証状態の
  明示管理 (VALIDATION 文化)」。先行研究は制御アルゴリズム寄りで、
  研究記録と物理モデルの整合管理を主題にしたものは見当たらない。

## 6. 作らない方がよいもの

- マクロ共振器全体の FDTD/FEM (計算量的に無意味; 連携は局所問題のみ)
- 汎用レンズ設計 (Zemax/CODE V の領域; 当プロジェクトの目的外)
- L3 物理光学の汎用 GUI 化を急ぐこと (まず CLI/解析 API で十分)

## 7. 主要出典 (web確認分)

- reZonator 2: https://github.com/orion-project/rezonator2 /
  http://rezonator.orion-project.org/
- RP Resonator: https://www.rp-photonics.com/resonator_design.html
- RP ProPulse: https://www.rp-photonics.com/rp_propulse.html
- LASCAD: http://www.hanamuraoptics.com/device/LASCAD/lascad_brochure.pdf
- 3DOptix: https://www.3doptix.com/
- LightPipes: https://opticspy.github.io/lightpipes/
- Pykat/Finesse: https://www.sciencedirect.com/science/article/pii/S2352711020303265
- LaserCAD: https://www.mdpi.com/2076-3417/15/22/11893
- self-tuning lasers: https://pmc.ncbi.nlm.nih.gov/articles/PMC5116642/ /
  https://arxiv.org/abs/1711.02702
