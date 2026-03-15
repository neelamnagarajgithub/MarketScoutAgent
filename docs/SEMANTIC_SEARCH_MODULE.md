# Semantic Search Module

File: `app/simple_semantic_search.py`

## Purpose

`SimpleSemanticSearch` is the retrieval entry point for the end-to-end market-intelligence system. It converts a user query into a large, structured, multi-source evidence bundle.

This stage is optimized for recall, source breadth, and resilience. It intentionally gathers more material than the final analysis needs, because downstream stages are responsible for safety, deduplication, and precision filtering.

## Position in the Full Runtime

The end-to-end flow is:

1. semantic search retrieves broad evidence
2. guardrails and judge reduce noise
3. analyzer generates structured business analysis
4. report generator creates the PDF
5. orchestrator persists metadata and uploads final artifact to Supabase

Because of that design, this module should be evaluated primarily on collection quality and fault tolerance, not on final-answer polish.

## Core Responsibilities

1. classify the user query
2. build a `SearchPlan`
3. schedule retrieval tasks by source family
4. execute provider calls concurrently
5. normalize results into a stable nested structure
6. persist a lightweight search session summary to the database

## Core Types

### `QueryType`

- `COMPANY_ANALYSIS`
- `MARKET_TREND`
- `PRODUCT_RESEARCH`
- `COMPETITOR_ANALYSIS`
- `FUNDING_INTELLIGENCE`
- `TECHNOLOGY_STACK`
- `NEWS_MONITORING`
- `GENERAL_INTELLIGENCE`

### `SearchPlan`

Fields:

- `query_type`
- `entities`
- `keywords`
- `sources`
- `search_terms`
- `financial_symbols`

`SearchPlan` is the contract that separates planning from execution.

## Query Planning

### Query optimization

`plan_search(query)` first calls the query optimizer. The optimizer contributes:

- keywords
- search-term expansions
- financial-symbol suggestions

### Query classification

`_classify_query(query)` maps the query to a broad intent class using keyword rules.

### Entity extraction

`_extract_entities(query)` identifies known companies or injects representative fallback entities when the query is too generic.

### Source-family selection

`_plan_sources(query_type)` chooses which families to activate.

Examples:

- company and funding flows activate financial, GitHub, business, startup, and social families
- product flows emphasize GitHub, community, and social signals
- technology-stack flows include security-oriented enrichment

### Search-term and symbol generation

The plan is finalized with bounded search terms and stock symbols to prevent excessive provider fan-out.

## Retrieval Families

Task builders currently exist for:

- search discovery
- news intelligence
- GitHub intelligence
- financial intelligence
- business intelligence
- social media
- community intelligence
- startup intelligence
- security intelligence

Not every family is used for every query.

## Task Builder Design

Each builder creates task descriptors that include:

- the source-family type
- the concrete provider name
- the query term or symbol
- the coroutine to execute

`_add_task(...)` is a defensive helper that prevents missing or non-callable fetchers from crashing the run.

This matters because some integrations are optional, dynamic, or scraper-backed.

## Async Execution

`execute_search(plan)`:

- assembles all task descriptors
- extracts coroutines and metadata
- runs them with `asyncio.gather(..., return_exceptions=True)`
- reattaches metadata to each result
- forwards results to `_process_task_results(...)`

The use of exception-tolerant gather is central to pipeline reliability.

## Normalization

`_process_task_results(...)` normalizes each provider-specific payload with `normalize_item(source, item)`.

The normalized output is stored in a nested structure grouped by family and provider, plus a `_metadata` summary.

This output is intentionally not flattened yet. Flattening occurs later in `LLMJudge._flatten_raw(...)`.

## Validation and Gating

Before executing retrieval, `validate_apis()` calls `APIKeyValidator.validate_all_keys()`.

Important behavior:

- providers are tested before use
- invalid providers are logged but do not necessarily block the run
- the search engine requires at least one viable search/news route to proceed usefully

## Final Response Shape

`_generate_final_response(...)` produces a bundle containing:

- query metadata
- query type
- plan summary
- total source and document counts
- high-level insights and recommendations
- `raw_data`

The `raw_data` field is the most important handoff to the judge stage.

## Persistence Behavior

Current runtime persistence behavior:

- saves a lightweight search-session summary to the database
- does not save local JSON result artifacts anymore

This changed when the system moved toward Supabase-backed persistence instead of local-file retention.

## Failure Model

This stage expects intermittent failures from third-party providers.

Typical failure causes:

- missing keys
- invalid keys
- provider quotas
- rate limiting
- scraper drift
- transient upstream outages

Resilience mechanisms:

- validation before execution
- safe task registration
- exception-tolerant gather
- per-item normalization guarded with `try/except`

## What This Module Does Not Do

It does not:

- sanitize prompt-injection deeply
- rank final relevance precisely
- build business recommendations
- render the PDF report

Those are downstream responsibilities.

## Related Docs

- `API_INTEGRATION_STATUS.md`
- `OPTIMIZER_INTEGRATION.md`
- `GUARDRAIL_AND_LLM_JUDGE.md`
