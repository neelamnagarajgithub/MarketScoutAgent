# Analysis Module

File: `app/pipeline/analyzer.py`

## Purpose

`AnalyzerAgent` transforms a validated `JudgedDataset` into a structured `AnalysisReport` that can be returned by the API, rendered as a PDF, and persisted by the orchestrator.

This stage is the synthesis layer of the system. It is responsible for turning evidence into product, market, and strategy meaning.

## Position in the Runtime

Input:

- `JudgedDataset`

Output:

- `AnalysisReport`

Consumers:

- `app/orchestrator.py`
- `app/pipeline/reporting.py`

## Primary Goals

- produce structured output instead of free-form prose
- remain useful even when the model is unstable
- guarantee a stable schema for the report layer
- expose fallback state clearly when the LLM path fails

## Output Contract

The analyzer returns:

- `summary`
- `key_findings`
- `risks`
- `recommendations`
- `confidence_score`
- `sections`

The `sections` map contains both narrative sections and machine-oriented support structures such as:

- `source_breakdown`
- `theme_breakdown`
- `timeline_breakdown`
- `evidence_highlights`
- `guardrail_summary`

## Analysis Flow

### Query-lens inference

`_infer_query_lens(query)` chooses the report framing.

Examples:

- competitor-style terms bias toward competitive intelligence
- funding terms bias toward financial and capital signals
- launch or feature terms bias toward product intelligence

This influences the narrative orientation of the prompt.

### Context construction

`_build_dataset_context(ds)` builds a compact structured context from the judged evidence set.

It includes:

- source counts
- source-type counts
- dominant terms
- monthly timeline distribution
- evidence samples
- guardrail flags
- judge notes

This means the model is reasoning over a curated evidence summary, not the entire raw retrieval corpus.

### Prompt generation

Primary generation uses `_build_prompt(context)`.

The prompt requires:

- strict JSON only
- section-level detail
- evidence-backed analysis
- explicit `evidence_highlights`
- a bounded confidence score

### Compact retry path

If the larger prompt proves unstable or too long, `_build_compact_prompt(context)` is used as a reduced-output fallback while keeping the same top-level schema.

### Parsing and repair pipeline

Successful HTTP responses from Gemini do not guarantee parseable JSON. The analyzer therefore uses multiple defensive helpers:

- `_response_to_text(...)`
- `_extract_balanced_json(...)`
- `_try_parse_candidate(...)`
- `_parse_llm_output(...)`
- `_repair_json_with_llm(...)`

Current parser behavior attempts to recover from:

- markdown-fenced JSON
- arrays containing a dict
- Python-literal-like dict output
- quoted JSON strings
- wrapper objects such as `report` or `analysis`

### Section normalization

`_normalize_sections(...)` guarantees that the report stage always receives a complete structure.

Important behaviors:

- missing sections are filled from deterministic context
- under-dense list sections are padded
- guardrail summary is kept high-level and report-safe

### Deterministic fallback

`_fallback(ds)` guarantees a usable report when:

- no judged items exist
- no Gemini key exists
- parse and repair fail
- model invocation throws an exception

Fallback uses evidence count, source diversity, dominant terms, and sampled titles to preserve some analytical value even without a valid LLM JSON response.

## Confidence Handling

Confidence is bounded to `[0.0, 1.0]`.

Fallback confidence is derived from evidence breadth and diversity so the system does not present sparse evidence as highly certain.

## Fallback Visibility

When the analyzer falls back, it adds a note like:

- `analyzer_fallback_reason=...`

The orchestrator then exposes:

- `analysis_mode`
- `fallback_reason`

This is the primary operational signal for analyzer health monitoring.

## Why This Stage Is Separate from the Judge

The judge answers: “Which evidence is safe and relevant enough to trust?”

The analyzer answers: “What strategic meaning should product and market teams draw from that evidence?”

Separating those concerns improves reliability and makes debugging much clearer.

## Related Docs

- `GUARDRAIL_AND_LLM_JUDGE.md`
- `REPORT_GENERATION_MODULE.md`
