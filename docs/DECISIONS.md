# DECISIONS.md — Architecture & Physics Decision Records

> **出自と位置づけ (laser-os への移植時に追記)**
> 本 ADR 群は姉妹設計プロジェクト `laser-research-os` で確定したもの。
> laser-os に移植した理由は、これらの設計判断が cavsim の既存実装の
> **裏付け**であり、research/ データ層の**規約**でもあるため。
> ADR 内の `data/` パスは research/ 構造に対応 (research/DATA_SCHEMA.md 参照)。
> `src/`・`tests/` への言及は研究データ用バリデータ等の将来想定。
>
> **cavsim (v0.2.1) との対応:**
> - ADR-0006 (ABCD 規約: t/s 分離, R·cosθ/R·secθ, m=(A+D)/2) は
>   cavsim.core が既に実装済み (docs/PHYSICS.md, tests/test_core.py と整合)。
> - ADR-0008 (GDD 符号・単位, per-bounce/per-pass) は cavsim の分散記帳と整合。
> - ADR-0003/0004 (PhysicalValue, 3 データレベル) は research/ データ層の規約で、
>   cavsim の計算用 JSON には未適用 (別系統)。
> ADR は追記専用 (append-only)。変更は新 ADR で supersede する (編集しない)。



<!-- ============================================================
MAINTENANCE METADATA
Purpose:      Append-only log of every significant design and physics
              decision (ADR style). Answers "why is it like this?" years
              later, and prevents silent convention changes.
Update when:  Before implementing any change to schemas, physics
              conventions, scope, tooling, or directory layout. New ADRs
              are appended; old ADRs are never edited — they are
              superseded by a new ADR that references them.
Risks if stale: Conventions drift silently (the classic sign-convention
              bug), rationale is lost, the same debates are re-fought,
              and analyses become irreproducible.
Coupled files: DATA_SCHEMA.md (schema ADRs), PROJECT.md (scope ADRs),
              CHANGELOG.md (every accepted ADR appears there),
              src/ docstrings (must cite convention ADRs).
============================================================ -->

Format per entry:

```
## ADR-XXXX: Title
Date | Status (proposed/accepted/superseded-by-ADR-YYYY) | Affects (files)
Context — Decision — Alternatives considered — Consequences
```

---

## ADR-0001: Files, not chat, are the source of truth
2026-06-11 | accepted | Affects: all
**Context:** The project must survive loss of any AI model and loss of all
chat history. **Decision:** All knowledge is persisted in versioned
repository files; every session ends by syncing chat results into files
(AI_INSTRUCTIONS.md §7). **Alternatives:** vendor "project memory"
features — rejected (lock-in, opaque). **Consequences:** more writing
discipline; full portability.

## ADR-0002: JSON records + Markdown docs as storage format
2026-06-11 | accepted | Affects: data/, docs/, DATA_SCHEMA.md
**Context:** Need a format readable by humans, any AI, and code for
decades. **Decision:** One JSON file per record under data/; Markdown for
documents; CSV for spectra/curves. No database server in v0.x.
**Alternatives:** SQLite (harder to diff/review; can be added later as a
*derived* index), YAML (ambiguity risks). **Consequences:** git-diffable
science data; a query layer can be generated from JSON at any time.

## ADR-0003: Mandatory PhysicalValue wrapper; null for unknown
2026-06-11 | accepted | Affects: DATA_SCHEMA.md §2, all data/
**Context:** Bare numbers lose units, conditions, and provenance; AI
models hallucinate "typical" values. **Decision:** Every physical quantity
is a PhysicalValue {value, unit, condition, source, confidence,
data_level, uncertainty}; unknown = null; multiple literature values are
kept as arrays, never silently averaged. **Consequences:** verbose files,
trustworthy science.

## ADR-0004: Three data levels; only `verified` feeds analysis
2026-06-11 | accepted | Affects: DATA_SCHEMA.md §1.4, AI_INSTRUCTIONS.md §2
**Context:** Mixing AI-extracted and human-checked data corrupts results.
**Decision:** raw → extracted → verified; promotion only by the human
researcher with a checkable source; engines refuse non-verified inputs
unless run in an explicitly labeled "exploratory" mode. **Consequences:**
slower data entry, publishable reliability.

## ADR-0005: Python ≥3.11 for engines; pure functions over data files
2026-06-11 | accepted | Affects: src/, tests/, README.md
**Context:** Need a scientific ecosystem (numpy/scipy) any future
contributor or AI knows. **Decision:** Python with pinned dependencies;
engines are pure functions: (twin + verified records + parameters) →
result objects; no hidden state, results carry engine_version and
inputs_hash. **Alternatives:** Julia (smaller talent pool), MATLAB
(license lock-in). **Consequences:** reproducibility; easy testing.

## ADR-0006: ABCD convention
2026-06-11 | accepted (amended at initial review 2026-06-11, see docs/session_notes/2026-06-11-t001-signoff.md) | Affects: src/ (v0.2), DATA_SCHEMA.md §8, docs/
**Decision:** Ray vector (y, θ) with θ in radians (paraxial); matrices
multiply right-to-left in propagation order (last element leftmost);
round-trip matrix is defined from a stated reference plane that every
result records; **the default reference plane is the output coupler
surface; any deviation from this default must be recorded per result**;
stability criterion |A+D| ≤ 2 with stability parameter
m = (A+D)/2; folded cavities are analyzed separately in tangential and
sagittal planes using the standard effective focal lengths for mirrors at
AOI (R·cosθ /2 tangential, R/(2·cosθ) sagittal — formula to be cited to a
textbook locator in the implementing docstring before v0.2 code lands).
**Consequences:** every ABCD result is reproducible and unambiguous, and
stability scans from different sessions are directly comparable by default.

## ADR-0007: Sign convention for radius of curvature
2026-06-11 | accepted (amended at initial review 2026-06-11, see docs/session_notes/2026-06-11-t001-signoff.md) | Affects: data/elements, DATA_SCHEMA.md §4
**Decision:** R > 0 means concave toward the incident beam (focusing
mirror) as stored in element records; the engine layer documents its
internal convention and converts explicitly at the boundary. The
convention is restated in every element record's `geometry` comment field
when ambiguity is possible. **Scope (amendment): this convention governs
reflective surfaces only. Transmissive curved surfaces (e.g., the curved
back face of an output-coupler substrate, lens surfaces), when they must
be recorded, state their own sign convention explicitly in the geometry
notes, pending a dedicated ADR if/when such surfaces enter analysis
(expected no later than v0.2).** **Context:** R-sign mistakes are the most
common cavity-design bug; centralizing the convention here prevents silent
flips.

## ADR-0008: Dispersion sign convention and units
2026-06-11 | accepted (amended at initial review 2026-06-11, see docs/session_notes/2026-06-11-t001-signoff.md) | Affects: data/, DATA_SCHEMA.md, docs/
**Decision:** GDD in fs², TOD in fs³; positive GDD = normal dispersion
(red travels faster than blue, longer wavelengths lead). **Reflective**
element GDD values are *per bounce*; **transmissive contributions
(amendment) are specified per single pass** (e.g., gain crystal as GDD/mm
× length per pass); budgets are reported *per round trip* with interaction
counts taken from the twin's `interactions_per_roundtrip` field, which
counts optical interactions per round trip — bounces for reflective
elements, passes for transmissive elements. **The field was renamed from
`bounces_per_roundtrip` at initial review, before any setup record
existed; therefore no data migration was required and schema_version
remains 0.1.0 (recorded in docs/migrations/SUPPORTED_VERSIONS.md).**
Fiber dispersion D in ps/(nm·km) with the D ↔ β₂ conversion recorded in
`source.derivation` whenever applied. **Consequences:** dispersion budgets
from different sessions are directly comparable, and reflective/transmissive
bookkeeping cannot be silently mixed.

## ADR-0009: Digital twin references records by id; never copies values
2026-06-11 | accepted | Affects: DATA_SCHEMA.md §6
**Context:** Copied values rot. **Decision:** Twins store only geometry,
roles, ids, and conditions; analyses join twin + verified records at run
time. Twin geometry changes increment `twin_version`; old versions are
deprecated, never deleted. **Consequences:** one source of truth per
property; full traceability from any result back to a cavity state.

## ADR-0010: Nonlinear extension reserved via PulseOutput interface
2026-06-11 | accepted (amended at initial review 2026-06-11, see docs/session_notes/2026-06-11-t001-signoff.md) | Affects: DATA_SCHEMA.md §8–9, ROADMAP.md
**Context:** v0.1 must not block future GNLSE/supercontinuum work.
**Decision:** `PulseOutput` is the sole oscillator→propagation interface;
`NonlinearMedium` and `PropagationSimulationResult` schemas are fixed now
(fields may be extended additively only). **Amendment: PulseOutput
reserves an optional additive field `field_file` for future measured
complex E-field amplitude/phase data (e.g., FROG or d-scan retrievals);
null until such measurements exist.** No GNLSE implementation before v0.6.
**Consequences:** the thesis pipeline (oscillator → SC) is architecturally
guaranteed, including a path from assumed pulse shapes to measured fields
without schema breakage.

## ADR-0011: No GUI before the data and engine layers are validated
2026-06-11 | accepted | Affects: ROADMAP.md, PROJECT.md
**Decision:** UI work (web app, dashboards) is Layer 4 and is not
scheduled before v0.7. Plots produced by engines (matplotlib to files) do
not count as UI. **Context:** flashy demos consume the budget that
validation needs.
