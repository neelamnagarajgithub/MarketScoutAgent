# Guardrail and LLM Judge Module

Files:

- `app/pipeline/guardrails.py`
- `app/pipeline/llm_judge.py`

## Purpose

This stage converts broad raw retrieval output into a high-quality, safe, relevance-focused evidence set for the analyzer.

It combines deterministic safety logic (`GuardrailEngine`) with model-assisted evidence selection (`LLMJudge`).

## Data Contract

Input to judge stage:

- Raw retrieval response from `SimpleSemanticSearch`

Output from judge stage:

- `JudgedDataset` from `app/pipeline/types.py`
  - `query`
  - `items: List[RetrievedItem]`
  - `dropped_count`
  - `guardrail_flags`
  - `judge_notes`

## GuardrailEngine Details

### Responsibilities

1. Normalize and sanitize text payloads
2. Redact sensitive patterns
3. Detect prompt-injection and policy-bypass content
4. Validate URL quality
5. Score text quality
6. Deduplicate records

### Important Methods

- `_normalize_text(text)`
- `sanitize(text)`
- `sanitize_metadata(metadata)`
- `redact_sensitive_data(text)`
- `is_blocked(text)`
- `is_valid_url(url)`
- `normalized_url(url)`
- `text_quality_score(item)`
- `classify_item_risks(item)`
- `deduplicate(items)`
- `enforce(items)`

### Filtering Logic

Items are dropped if:

- Prompt injection/policy bypass risk is detected
- URL quality is poor and overall score is low
- Text quality score is below threshold
- Duplicate fingerprint already seen

Guardrail flags summarize aggregate effects, for example:

- `blocked_items=...`
- `invalid_urls_detected=...`
- `low_quality_items_removed=...`
- `duplicates_removed=...`
- `content_sanitization_applied=true`

## LLMJudge Details

### Responsibilities

1. Flatten nested retrieval output into `RetrievedItem` objects
2. Run guardrails over all candidate items
3. Score relevance heuristically
4. Enforce source diversity
5. Optionally refine keep/drop with Gemini

### Main Flow (`judge`)

1. `_flatten_raw(raw_results)`
2. `guardrails.enforce(items)`
3. `_heuristic_score(query, item)` for each item
4. weak-cutoff filter (`>= 0.08`)
5. `_diversity_select(...)`
6. `_llm_validate(...)` if Gemini key exists
7. return `JudgedDataset`

### Scoring Features

Heuristic scoring blends:

- Query term overlap
- Source reliability weighting (`_source_weight`)
- Guardrail quality score
- Content richness
- Optional recency bonus

### Diversity Strategy

`_diversity_select` performs round-robin selection from per-source ranked lists so one source cannot dominate the evidence set.

## Model Usage

If key is available, `LLMJudge` initializes:

- `ChatGoogleGenerativeAI(model="gemini-2.5-flash")`

If key is absent or model call fails, judge remains functional using deterministic heuristics.

## Why This Stage Matters

Without this stage, the analyzer receives noisy, duplicated, and potentially unsafe context, which increases hallucination risk and lowers recommendation quality.

This stage therefore acts as the precision gate between raw retrieval and strategic analysis.
