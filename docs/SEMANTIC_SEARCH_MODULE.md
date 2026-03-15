# Semantic Search Module

File: `app/simple_semantic_search.py`

## Purpose

`SimpleSemanticSearch` is the retrieval engine that turns a natural-language query into a large normalized evidence dataset from multiple provider families (search, news, code, financial, social, startup, and security).

It is designed for breadth-first intelligence collection with strong operational resilience:

- Async fan-out over many sources
- Safe task registration to avoid pipeline crashes on missing fetchers
- Per-result normalization into one common schema
- Query planning based on intent class

## Core Responsibilities

1. Query understanding and planning
2. Source-family selection by query type
3. Async task creation and execution
4. Data normalization and packaging
5. Session persistence and JSON export

## Key Types

### `QueryType` enum

- `COMPANY_ANALYSIS`
- `MARKET_TREND`
- `PRODUCT_RESEARCH`
- `COMPETITOR_ANALYSIS`
- `FUNDING_INTELLIGENCE`
- `TECHNOLOGY_STACK`
- `NEWS_MONITORING`
- `GENERAL_INTELLIGENCE`

### `SearchPlan` dataclass

Fields:

- `query_type`
- `entities`
- `keywords`
- `sources`
- `search_terms`
- `financial_symbols`

## Retrieval Lifecycle

### 1) Plan Phase

Methods:

- `plan_search(query)`
- `_classify_query(query)`
- `_extract_entities(query)`
- `_plan_sources(query_type)`
- `_generate_search_terms(query, entities, keywords)`
- `_map_to_symbols(entities)`

Output: `SearchPlan` used downstream by task builders.

### 2) Task Builder Phase

Task-family builders:

- `_create_search_tasks`
- `_create_news_tasks`
- `_create_github_tasks`
- `_create_financial_tasks`
- `_create_business_intelligence_tasks`
- `_create_social_media_tasks`
- `_create_community_tasks`
- `_create_startup_tasks`
- `_create_security_tasks`

Important behavior:

- `_add_task(...)` prevents non-callable fetchers from breaking the run.
- Optional fetchers are dynamically resolved via `getattr` with fallback names.

### 3) Async Execution Phase

`execute_search(plan)`:

- Builds a flat list of task descriptors with metadata (`type`, `source`, `query`, `coro`)
- Executes coroutines with `asyncio.gather(*coroutines, return_exceptions=True)`
- Re-attaches metadata to each completed result
- Passes output to `_process_task_results`

### 4) Normalization and Packaging

`_process_task_results(task_results)`:

- Normalizes each raw item through `normalize_item(source, item)`
- Organizes results by source family and source name
- Computes task-level success metadata

Result shape includes:

- `search_discovery`
- `news_intelligence`
- `github_intelligence`
- `financial_intelligence`
- `business_intelligence`
- `social_media`
- `community_intelligence`
- `startup_intelligence`
- `security_intelligence`
- `_metadata`

### 5) Final Response and Persistence

`comprehensive_search(query)`:

- Validates available APIs
- Plans and executes retrieval
- Builds response with summary, insights, and recommendations
- Saves one internal session record to DB (`_save_search_session`)
- Saves a full JSON file under `search_results/` (`_save_json_file`)

## API/Key Handling Strategy

Dynamic key lookup is centralized in `_key(*names)` so config variants remain compatible.

Examples:

- `GOOGLE_API_KEY`, `google_api_key`, etc. are handled where relevant
- Missing keys usually skip one provider rather than failing the full search

## Source Coverage Strategy

The module intentionally mixes high-signal and high-volume sources:

- High-signal: financial/news/search/code sources
- Community sentiment: reddit/hackernews/mastodon
- Emerging signal streams: startup/security/social feeds

Then downstream judge/guardrails reduce noise.

## Failure Handling

Built-in tolerance includes:

- Task-creation failures are logged and skipped
- Execution exceptions are captured and do not terminate the pipeline
- Per-item normalization exceptions are isolated

This design keeps recall high while preserving runtime stability.

## Outputs Consumed by Next Stage

Output is consumed by `LLMJudge` in `app/pipeline/llm_judge.py`.

`LLMJudge` flattens `raw_data` into `RetrievedItem` records and performs guardrail + relevance filtering before analysis.
