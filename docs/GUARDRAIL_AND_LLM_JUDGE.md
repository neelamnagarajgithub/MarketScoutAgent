# Guardrail and LLM Judge Module

Files:

- `app/pipeline/guardrails.py`
- `app/pipeline/llm_judge.py`

## Purpose

This stage is the pipeline’s safety and precision gate.

The semantic-search stage intentionally over-collects. That raw retrieval bundle can contain duplicated evidence, low-signal snippets, malformed URLs, noisy markup, and even prompt-injection-like text embedded in scraped content. The job of this stage is to reduce that broad set into a smaller, safer, and more analytically useful dataset.

## Position in the End-to-End Flow

Input:

- nested retrieval output from `SimpleSemanticSearch`

Output:

- `JudgedDataset`

Downstream consumer:

- `AnalyzerAgent`

This is the point where the pipeline stops being “broad collection” and starts being “trusted evidence curation.”

## Data Contracts

### Raw input

The input is a nested structure grouped by source family, source name, and query key.

### Output

`JudgedDataset` contains:

- `query`
- `items`
- `dropped_count`
- `guardrail_flags`
- `judge_notes`

Each item is a `RetrievedItem` with normalized fields such as title, URL, source type, source name, content, publication date, and metadata.

## GuardrailEngine

### Responsibilities

1. normalize text
2. sanitize markup and code noise
3. redact secret-like patterns
4. identify prompt-injection or bypass text
5. validate URL quality
6. score content quality
7. deduplicate near-identical items

### Key methods

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

### Sanitization behavior

The guardrail layer removes or reduces:

- raw HTML tags
- fenced code blocks
- data-URI payload fragments
- email addresses and phone numbers
- common token/key patterns
- excessive whitespace and formatting noise

This makes the downstream LLM context safer and cleaner.

### Risk classification

The system flags content resembling:

- prompt injection
- system or developer prompt exfiltration attempts
- low-quality or malformed payloads
- invalid or missing URLs
- suspicious markup noise
- token-like secrets in text

### Quality scoring

Quality scoring is heuristic and intentionally cheap. It uses factors such as:

- title length
- content length
- URL validity
- alphabetic ratio in content
- timestamp presence
- metadata presence

This is not a factual-truth engine. It is a low-cost signal for weeding out obviously weak content.

### Deduplication

Deduplication uses a fingerprint built from normalized URL, normalized title, and normalized content prefix. It is designed to remove obvious duplicates, not to solve semantic clustering.

### Output flags

Examples:

- `blocked_items=...`
- `invalid_urls_detected=...`
- `low_quality_items_removed=...`
- `duplicates_removed=...`
- `content_sanitization_applied=true`

These are useful both for debugging and for understanding how much of the retrieval corpus was discarded before analysis.

## LLMJudge

### Responsibilities

1. flatten nested retrieval output into `RetrievedItem` objects
2. run guardrails
3. score relevance heuristically
4. preserve source diversity
5. optionally use Gemini for keep/drop refinement

### Flattening

`_flatten_raw(raw_results)` walks the nested retrieval structure and extracts usable document-like payloads into one uniform evidence model.

This is where heterogeneous provider output becomes analyzer-ready evidence.

### Heuristic ranking

The judge uses deterministic ranking before involving the model.

Important helpers:

- `_source_weight(...)`
- `_heuristic_score(...)`
- `_heuristic_rank(...)`

The heuristic score blends:

- query-term overlap
- source-weight priors
- guardrail quality score
- recency bonus
- content richness

### Diversity control

Two mechanisms help avoid one source dominating the evidence set:

- `_diversify(...)`
- `_diversity_select(...)`

`_diversity_select(...)` performs round-robin selection across per-source ranked lists.

### Optional Gemini validation

If a Gemini key is available, `_llm_validate(...)` sends a compressed evidence set to `gemini-2.5-flash` and asks for `keep_indices` in strict JSON.

If the model is unavailable or the validation step fails, the judge safely falls back to heuristic selection.

### Main runtime flow

`judge(query, raw_results)` performs:

1. flatten
2. guardrail enforcement
3. weak relevance cutoff
4. diversity selection
5. optional LLM keep-set validation
6. `JudgedDataset` construction

## Why This Stage Matters

Without this stage, the analyzer would be forced to reason over too much noisy or unsafe input. That would degrade recommendation quality and increase malformed downstream LLM output.

This stage exists to make the analyzer’s job smaller, cleaner, and more reliable.

## Failure Behavior

This module is designed to degrade safely under:

- malformed retrieval payloads
- missing URLs
- low-quality text
- absent Gemini key
- Gemini keep/drop validation failure

Even in those cases, a heuristic-only `JudgedDataset` can still be produced and passed downstream.

## Related Docs

- `SEMANTIC_SEARCH_MODULE.md`
- `ANALYSIS_MODULE.md`
