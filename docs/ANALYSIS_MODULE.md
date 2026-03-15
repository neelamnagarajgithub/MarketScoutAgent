# Analysis Module

File: `app/pipeline/analyzer.py`

## Purpose

`AnalyzerAgent` converts a validated `JudgedDataset` into a structured `AnalysisReport` suitable for strategic decision-making and PDF rendering.

It combines:

- Deterministic dataset introspection
- Strict JSON schema prompting
- Robust parsing and JSON repair
- Safe fallback synthesis

## Input and Output

Input:

- `JudgedDataset` (`query`, validated `items`, guardrail/judge notes)

Output:

- `AnalysisReport`
  - `summary`
  - `key_findings`
  - `risks`
  - `recommendations`
  - `confidence_score`
  - `sections` (deep structured map)

## Analysis Strategy

### 1) Query Lens Inference

`_infer_query_lens(query)` classifies the business framing:

- Competitive intelligence
- Funding intelligence
- Product intelligence
- Generic market intelligence

This informs the narrative orientation used in prompts.

### 2) Context Construction

`_build_dataset_context(ds)` composes a compact but rich context object with:

- Source breakdown (`_source_breakdown`)
- Theme breakdown (`_theme_breakdown`)
- Timeline breakdown (`_timeline_breakdown`)
- Evidence samples (`_evidence_samples`)
- Guardrail and judge notes

### 3) LLM Generation

Primary prompt:

- `_build_prompt(context)`
- Requires strict JSON-only output
- Enforces density and section-level depth targets

Compact prompt fallback:

- `_build_compact_prompt(context)`
- Used when token truncation is detected

### 4) Parse and Repair Pipeline

Resilience helpers:

- `_response_to_text(resp)`
- `_extract_balanced_json(text)`
- `_try_parse_candidate(candidate)`
- `_parse_llm_output(text)`
- `_repair_json_with_llm(raw_output, prompt)`

If model output is malformed, repair is attempted before fallback is triggered.

### 5) Section Normalization

`_normalize_sections(sections, context)` guarantees required keys exist and minimum list density is maintained, so downstream report generation never receives sparse or missing sections.

### 6) Fallback Synthesis

`_fallback(ds)` produces a deterministic report when:

- No items are available
- LLM is unavailable
- Parsing and repair fail

Fallback includes explicit judge note:

- `analyzer_fallback_reason=...`

This is surfaced to API consumers through orchestrator metadata.

## Confidence Handling

Confidence score is bounded to `[0.0, 1.0]`. Fallback confidence is derived from evidence count and source diversity to avoid misleading certainty.

## Operational Guarantees

The module guarantees the caller always receives a valid `AnalysisReport` object, even during provider/model instability.

This guarantee is critical for uptime of PDF and persistence stages.
