# DATA_SCHEMA.md — research/ データ構造と規約 (schema_version 0.1.0)

> **出自と位置づけ (laser-os への移植時に追記)**
> 本スキーマは、姉妹設計プロジェクト `laser-research-os` (設計先行・コード未実装)
> で確定した完成版データ設計を、laser-os の `research/` 構造へ移植したもの。
> パスは laser-os に合わせて調整済み (data/materials → research/matdb/materials 等)。
> **適用範囲は `research/` 配下の研究データのみ。** cavsim の計算用 JSON
> (`examples/*.json`, schema_version=1) はこの設計とは別系統で、当面そのまま。
> 両者の統合が必要になった場合は ADR を書いてから行う (research/DECISIONS.md)。
> このスキーマに沿った実データの投入は段階的に行う (現在 research/ は枠組み)。

---

(以下、原設計のまま。`src/`・`tests/` への言及は将来 research 用バリデータを
置く場合の想定であり、現状の cavsim のコード/テストとは無関係。)

# DATA_SCHEMA.md — Data Structures and Conventions (schema_version 0.1.0)

<!-- ============================================================
MAINTENANCE METADATA
Purpose:      Single authoritative definition of every data structure in
              data/ and every cross-cutting convention (units, IDs,
              data levels, versioning). Code and AI must conform to this
              file, never the other way around.
Update when:  Only via the change process in AI_INSTRUCTIONS.md §5:
              ADR first, then this file, then data migration, then
              CHANGELOG.md. Bump schema_version per §1.2.
Risks if stale: Data files diverge from documentation; analyses read
              fields that mean something else; silent physics corruption.
              This is the highest-risk file in the repository.
Coupled files: DECISIONS.md (every schema change is an ADR),
              CHANGELOG.md, all files under research/, validators in
              src//tests/, examples/.
============================================================ -->

## 1. Global conventions

### 1.1 File format and identity

- All data records are JSON (UTF-8), one record per file.
- Every record has: `id` (stable, human-readable, kebab-case, prefixed:
  `mat-`, `elem-`, `paper-`, `exp-`, `setup-`), `schema` (record type name),
  `schema_version`, `created`, `modified` (ISO 8601 dates), `status`
  (`active` | `deprecated`), `notes` (free text, may be empty).
- IDs are never reused or renamed; deprecate and create a new record.

### 1.2 Schema versioning

- `schema_version` is semver. PATCH: clarifications, no data changes.
  MINOR: additive optional fields (old files remain valid). MAJOR: breaking
  change — requires an ADR, a migration note in `docs/migrations/`, and a
  migration of all affected files in the same change.
- Validators in `tests/` must accept all non-deprecated versions listed in
  `docs/migrations/SUPPORTED_VERSIONS.md`.

### 1.3 Units

- Unit strings are mandatory and explicit; SI with these standard
  laser-physics exceptions allowed: `nm`, `um`, `mm`, `cm`, `fs`, `ps`, `ns`,
  `mW`, `W`, `kW`, `MW`, `nJ`, `uJ`, `mJ`, `fs^2`, `fs^3`, `fs^2/mm`,
  `cm^2` (cross sections), `W/(m*K)`, `1/K`, `%`, `deg`, `degC`, `K`,
  `MHz`, `GHz`, `THz`, `ps/(nm*km)` (fiber D), `1/(W*km)` (γ), `W/m^2`,
  `J/cm^2` (fluence).
- One value, one unit. Never encode units in field names.
- Derived/converted values record the conversion in `source.derivation`.

### 1.4 Data levels

Every `PhysicalValue` and every record carries `data_level`:

1. `raw` — as captured (lab notebook photo transcription, instrument dump,
   verbatim quote from a paper). Immutable.
2. `extracted` — structured by a human or AI from a raw source. May contain
   errors; not analysis-grade.
3. `verified` — checked by the human researcher against the primary source
   or own measurement. **Only `verified` data may feed analysis engines.**

Promotion `raw → extracted → verified` is recorded in the record's
`provenance` list (who/what, date, from-level, to-level, check performed).

## 2. PhysicalValue (used everywhere)

```json
{
  "value": null,
  "unit": "cm^2",
  "condition": "T = 300 K, E||c polarization, peak at signal wavelength",
  "source": {
    "type": "paper",            
    "ref": "paper-doi-10-XXXX-XXXXX",
    "locator": "Table 2",
    "derivation": null
  },
  "confidence": "unverified",
  "data_level": "extracted",
  "uncertainty": null
}
```

- `value`: number, array of numbers, or `null` (unknown). Never a string.
- `condition`: free text stating temperature, polarization, wavelength,
  doping, measurement method — whatever the value depends on. Required;
  use `""` only if truly condition-free.
- `source.type`: `paper` | `datasheet` | `own_measurement` | `textbook` |
  `ai_model` | `derived`. `ref` points to a `paper-` id, an `exp-` id, a
  vendor document stored in `docs/datasheets/`, or names the AI model.
- `source.derivation`: if `type: derived`, the formula/conversion and input
  refs.
- `confidence`: `verified` | `plausible` | `unverified` | `disputed`.
  `verified` here must agree with `data_level: verified`.
- `uncertainty`: `{ "value": number|null, "type": "stddev"|"range"|"digit" }`
  or `null`.

Multiple literature values for the same property are stored as an **array of
PhysicalValue objects** under that property — never averaged silently.

## 3. Material record (`research/matdb/materials/mat-*.json`)

Designed for *any* gain medium (Yb:YAG, Yb:FAP, Yb:KGW, Yb:CALGO,
Ti:Sapphire, Nd:YAG, future). Anisotropy is handled per-axis; isotropic
materials use a single `axes: ["iso"]` entry.

```json
{
  "id": "mat-yb-yag",
  "schema": "Material",
  "schema_version": "0.1.0",
  "name": "Yb:YAG",
  "host": "Y3Al5O12",
  "dopant": { "ion": "Yb3+", "concentration": [/* PhysicalValue[], e.g. at.% */] },
  "category": "gain_crystal",
  "crystal_system": "cubic",
  "axes": ["iso"],
  "spectroscopy": {
    "absorption_cross_section": { "iso": [/* PhysicalValue[] (peak values; spectra go in spectra_files) */] },
    "emission_cross_section":   { "iso": [] },
    "absorption_peaks_nm":      { "iso": [] },
    "emission_peaks_nm":        { "iso": [] },
    "upper_state_lifetime":     [],
    "gain_bandwidth":           { "iso": [] },
    "quantum_defect":           [],
    "laser_scheme": null
  },
  "optical": {
    "refractive_index": { "iso": [] },
    "sellmeier": { "iso": { "form": null, "coefficients": null, "valid_range_nm": null, "source": null } },
    "dn_dT": { "iso": [] },
    "gdd_per_mm": { "iso": [] },
    "nonlinear_index_n2": { "iso": [] }
  },
  "thermal": {
    "thermal_conductivity": { "iso": [] },
    "thermal_expansion":    { "iso": [] },
    "fracture_limit":       []
  },
  "mechanical": { "hardness_mohs": [], "hygroscopic": null },
  "spectra_files": [
    { "kind": "emission_cross_section", "path": "research/matdb/materials/spectra/...", "format": "csv:wavelength_nm,sigma_cm2", "source": null, "data_level": "raw" }
  ],
  "provenance": [],
  "status": "active",
  "created": "2026-06-11",
  "modified": "2026-06-11",
  "notes": ""
}
```

Rules: empty arrays mean "no data yet" — they are not errors. `category`
also covers `nonlinear_crystal`, `substrate`, `fiber` (see §9 for
fiber-specific extension via `nonlinear` block).

## 4. OpticalElement record (`research/optdb/elements/elem-*.json`)

One schema, discriminated by `element_type`:
`mirror_flat` | `mirror_curved` | `output_coupler` | `chirped_mirror` |
`gti_mirror` | `sesam` | `lens` | `prism` | `plate` | `dichroic` |
`gain_module` | `other`.

Common block:

```json
{
  "id": "elem-oc-1pct-example",
  "schema": "OpticalElement",
  "schema_version": "0.1.0",
  "element_type": "output_coupler",
  "name": "",
  "vendor": null,
  "part_number": null,
  "datasheet_ref": null,
  "geometry": {
    "radius_of_curvature": [/* PhysicalValue[]; sign convention: ADR-0007 */],
    "diameter": [],
    "thickness": [],
    "wedge": [],
    "substrate_material_ref": null
  },
  "coating": {
    "design_wavelength_nm": [],
    "aoi_deg": [],
    "polarization": null,
    "reflectivity": [],
    "transmission": [],
    "reflectivity_curve_file": null,
    "gdd": [/* PhysicalValue[] in fs^2 — per bounce for reflective elements, per single pass for transmissive elements; sign convention: ADR-0008 (amended) */],
    "gdd_curve_file": null,
    "ldt": []
  },
  "provenance": [],
  "status": "active",
  "created": "2026-06-11",
  "modified": "2026-06-11",
  "notes": ""
}
```

Type-specific blocks (present only when relevant):

- `sesam`: `{ "modulation_depth": [], "saturation_fluence": [],
  "non_saturable_loss": [], "recovery_time": [], "damage_fluence": [] }`
- `lens`: `{ "focal_length": [], "lens_material_ref": null, "ar_coating": null }`
- `prism`: `{ "apex_angle": [], "prism_material_ref": null }`
- `gain_module`: `{ "material_ref": "mat-...", "length": [], "doping": [],
  "cut": null, "orientation": null, "cooling_geometry": null }`

GDD curves (GDD vs wavelength) are stored as CSV files referenced by
`gdd_curve_file` with format `csv:wavelength_nm,gdd_fs2`, each with its own
source and data_level in a sidecar entry inside `provenance`.

## 5. Paper record (`research/litdb/sources/paper-*.json`)

```json
{
  "id": "paper-doi-10-XXXX-XXXXX",
  "schema": "Paper",
  "schema_version": "0.1.0",
  "doi": null,
  "title": "",
  "authors": [],
  "year": null,
  "venue": "",
  "bibtex": "",
  "pdf_path": null,
  "tags": ["yb-fap", "kerr-lens-mode-locking"],
  "relevance": "",
  "extracted_values": [
    {
      "target": "mat-yb-fap.spectroscopy.emission_cross_section",
      "physical_value_summary": "see material record entry sourced to this paper",
      "extracted_by": "human|ai_model:<name>",
      "extraction_date": "2026-06-11",
      "data_level": "extracted"
    }
  ],
  "key_claims": [
    { "claim": "", "locator": "Sec. 3", "kind": "FACT|ASSUMPTION|RESULT" }
  ],
  "ai_summary": { "text": null, "model": null, "date": null, "is_primary_source": false },
  "provenance": [],
  "status": "active",
  "created": "2026-06-11",
  "modified": "2026-06-11",
  "notes": ""
}
```

`ai_summary.is_primary_source` is hard-coded `false` by definition.
Extracted numeric values live in the *target* material/element records as
PhysicalValues whose `source.ref` points back here; `extracted_values` is
the reverse index.

## 6. DigitalTwin / CavitySetup record (`research/optdb/setups/setup-*.json`)

The twin is an **ordered sequence of stations along the beam path**, plus a
pump section and environment. It is the single input to ABCD, stability,
and dispersion analysis.

```json
{
  "id": "setup-example-oscillator-v1",
  "schema": "CavitySetup",
  "schema_version": "0.1.0",
  "name": "",
  "cavity_type": "linear|ring|z_fold|x_fold|other",
  "design_wavelength_nm": null,
  "target_rep_rate": [],
  "pump": {
    "source": { "kind": "diode|fiber_coupled_diode|laser", "wavelength": [], "max_power": [], "beam_quality_m2": [], "fiber_core_diameter": [], "fiber_na": [], "ref": null },
    "optics": [ { "element_ref": "elem-...", "distance_from_previous": [], "notes": "" } ],
    "conditions": { "set_power": [], "spot_size_in_crystal": [], "polarization": null }
  },
  "beam_path": [
    {
      "station": 1,
      "element_ref": "elem-...  (or 'mat-...' via a gain_module element)",
      "role": "end_mirror|fold_mirror|gain|oc|sesam|chirped_mirror|gti|lens|other",
      "distance_to_next": { "value": null, "unit": "mm", "condition": "measured along beam axis", "source": {"type": "own_measurement", "ref": null, "locator": null, "derivation": null}, "confidence": "unverified", "data_level": "extracted", "uncertainty": null },
      "aoi_deg": [],
      "plane_notes": "tangential/sagittal relevant if folded",
      "interactions_per_roundtrip": 1
    }
  ],
  "environment": {
    "cooling": { "method": null, "coolant_temperature": [], "mount": null },
    "room_temperature": [],
    "humidity": [],
    "enclosure": null
  },
  "dispersion_budget_ref": null,
  "linked_experiments": ["exp-..."],
  "twin_version": 1,
  "as_built_date": null,
  "provenance": [],
  "status": "active",
  "created": "2026-06-11",
  "modified": "2026-06-11",
  "notes": "Distances are physical; engines compute optical path using element refractive indices."
}
```

Rules:
- The twin references elements/materials by id; it never copies their
  properties. Analysis joins twin + verified records at run time.
- `interactions_per_roundtrip` counts optical interactions per round trip:
  bounces for reflective elements, passes for transmissive elements
  (ADR-0008, amended at initial review; renamed from
  `bounces_per_roundtrip` before any setup record existed).
- Geometry changes on the real table → increment `twin_version` and record
  the change in the linked experiment log. Old versions are kept
  (`status: deprecated`), enabling "which cavity produced which result".

## 7. ExperimentLog record (`research/expdb/logs/exp-*.json`)

```json
{
  "id": "exp-2026-06-11-a",
  "schema": "ExperimentLog",
  "schema_version": "0.1.0",
  "date": "2026-06-11",
  "operator": "",
  "setup_ref": "setup-...",
  "twin_version": 1,
  "goal": "",
  "changes_made": [ { "description": "", "station": null, "before": null, "after": null } ],
  "conditions": { "pump_power": [], "coolant_temperature": [], "room_temperature": [] },
  "measurements": [
    { "quantity": "output_power|spectrum|rf_spectrum|autocorrelation|beam_profile|other",
      "result": [/* PhysicalValue[] for scalars */],
      "data_file": null,
      "instrument": "",
      "data_level": "raw" }
  ],
  "observations": "",
  "interpretation": { "facts": [], "assumptions": [], "open_questions": [] },
  "outcome": "success|partial|failure|n/a",
  "next_actions": [],
  "provenance": [],
  "status": "active",
  "created": "2026-06-11",
  "modified": "2026-06-11",
  "notes": ""
}
```

Logs are append-only history: never deleted, never rewritten after the
fact (corrections go in `notes` with date).

## 8. Analysis schemas (engine I/O, v0.2+)

Defined now so engines and the twin co-evolve without breaking changes.

- `ABCDAnalysisResult`: `{ setup_ref, twin_version, wavelength_nm, plane:
  "tangential"|"sagittal", roundtrip_matrix: [[A,B],[C,D]], stability_parameter,
  is_stable, beam_radius_at_stations: [{station, w_um}], waist: {location_mm,
  w0_um}, engine_version, conventions_ref: "ADR-0006", inputs_hash, date }`
- `StabilityScanResult`: same plus the scanned parameter
  (`{parameter_path, values, stability_curve, mode_size_curve}`).
- `DispersionBudget`: `{ setup_ref, twin_version, wavelength_nm,
  contributions: [{station, element_ref, gdd_fs2, tod_fs3, per_roundtrip}],
  total_gdd_fs2_per_roundtrip, total_tod_fs3_per_roundtrip,
  conventions_ref: "ADR-0008", engine_version, inputs_hash, date }` —
  per-round-trip contributions use the twin's `interactions_per_roundtrip`
  (bounces for reflective, passes for transmissive; ADR-0008 amended).
- `PulseOutput` (also the hand-off object to the nonlinear extension):
  `{ setup_ref, twin_version, center_wavelength_nm, rep_rate, average_power,
  pulse_energy, pulse_duration_fs, duration_definition: "FWHM_sech2|FWHM_gauss|...",
  spectrum_file, spectral_bandwidth_nm, time_bandwidth_product, peak_power,
  chirp_gdd_fs2, beam: {m2, w0_um},
  field_file: null /* reserved (ADR-0010 amended): optional path to measured
  complex E-field amplitude/phase data (e.g., FROG/d-scan retrieval), with
  format and retrieval method recorded in its provenance; null until such
  a measurement exists */,
  data_level, source }`
  — every numeric field is a PhysicalValue; `peak_power` may be `derived`.

Engine results are *derived artifacts*, written to `examples/` or report
folders — never into `research/` source records. `inputs_hash` makes results
reproducible and detects stale analyses.

## 9. Nonlinear / supercontinuum extension (reserved, v0.6+)

Reserved schemas — fields fixed now, implementation later:

- `NonlinearMedium` (a `Material` with `category: "fiber"` or
  `nonlinear_crystal` plus block `nonlinear`):
  `{ "fiber_type": "PCF|HNLF|SMF|bulk|waveguide", "gamma": [/* 1/(W*km) */],
  "zero_dispersion_wavelength": [], "dispersion_D": [/* ps/(nm*km) */],
  "beta_coefficients": { "beta2": [], "beta3": [], "beta4": [],
  "reference_wavelength_nm": null }, "effective_mode_area": [],
  "attenuation": [], "length_available": [], "damage_threshold": [],
  "raman_fraction_fr": [], "dispersion_curve_file": null }`
- `PropagationSimulationResult`: `{ input_pulse_ref: "<PulseOutput>",
  medium_ref, length, model: "GNLSE|NLSE|analytic_estimate", solver: {name,
  version, step_control}, numerical_grid: {n_points, time_window_ps},
  outputs: {output_spectrum_file, output_temporal_file, spectrogram_file},
  derived: { soliton_order_N: [], b_integral: [], fission_length: [],
  coherence_metric: [] }, conventions_ref, inputs_hash, date, data_level }`

Compatibility contract: `PulseOutput` (§8) is the only interface between
the oscillator side and the propagation side. Soliton order and B-integral
are *derived* PhysicalValues with `source.type: "derived"` and the formula
recorded in `source.derivation`.

## 10. Validation data (`examples/`, `tests/`)

Every engine ships with validation cases stored as
`examples/validation/val-*.json`:
`{ id, engine, description, inputs (inline or refs), expected_output,
expected_source (textbook eq./paper with locator), tolerance,
data_level: "verified" }`.
Examples: two-mirror cavity stability against the analytic g1·g2 criterion;
known material-dispersion GDD against published curves (source required);
a published oscillator design reproduced from its paper. A test that lacks
an authoritative `expected_source` is a smoke test, not validation, and
must be labeled as such.
