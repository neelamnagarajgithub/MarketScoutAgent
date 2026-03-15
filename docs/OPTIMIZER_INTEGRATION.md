# Query Optimizer Integration

File: `app/query_optimizer.py`

## Purpose

The query optimizer is a deterministic pre-retrieval planning component. It improves the quality of the inputs fed into the search engine without requiring an LLM round-trip.

It helps with:

- keyword extraction
- search-term expansion
- financial-symbol mapping
- optional result filtering helpers for future use

## Where It Is Integrated Today

Current live integration point:

- `SimpleSemanticSearch.plan_search(query)` calls `self.query_optimizer.optimize_query(query)`

The optimizer output populates:

- `keywords`
- `search_terms`
- `financial_symbols`

These values then drive search and financial task creation.

## Important Clarification

The optimizer contains a `filter_search_results(...)` helper, but that helper is not currently wired into the runtime retrieval path. It exists as a useful extension point, not as an active production-stage filter today.

## Main Methods

### `optimize_query(query)`

This is the entry point used by the search engine. It returns a dictionary containing:

- `keywords`
- `search_terms`
- `financial_symbols`
- `original_query`

### `_extract_keywords(query)`

Behavior:

- tokenizes lowercase words
- removes short/common stopwords
- adds a few compound phrases such as `artificial intelligence` and `startup funding`
- caps the keyword set to keep planning bounded

### `optimize_search_terms(query)`

Behavior:

- keeps the original query as the highest-priority term
- adds context-aware phrase expansions for AI, funding, market, and certain company names
- removes near-duplicate phrases using `_are_similar`
- limits the output list to control provider fan-out

### `enhance_financial_symbols(query)`

Behavior:

- maps recognized company names to stock symbols
- adds AI-heavy symbol sets when the query is AI-oriented
- adds venture/startup-biased symbol sets for funding queries
- falls back to major technology companies for generic queries

### `filter_search_results(results)`

Behavior:

- removes obvious noise categories such as dictionary pages, sports, weather, cooking, and celebrity gossip
- checks title and content for domain-relevant keywords
- retains only results above a simple relevance threshold

Current status:

- implemented
- not currently invoked by `SimpleSemanticSearch`

## End-to-End Effect on Search Quality

The optimizer affects search quality before any network request is made.

Without optimizer support:

- search terms are more literal
- symbol extraction is weaker
- broad queries are less likely to activate useful financial sources

With optimizer support:

- search phrases are more domain-aware
- retrieval gets better query anchors
- financial enrichment is more likely to occur on relevant queries

## Tradeoffs

Strengths:

- deterministic
- fast
- cheap
- easy to reason about

Limitations:

- handcrafted rules rather than learned behavior
- domain vocabulary is static
- result-filter helper is not yet part of main execution
- symbol mapping is heuristic and sometimes indirect

## Recommended Improvements

1. Wire `filter_search_results(...)` into post-fetch processing
2. Move phrase templates and stopwords into configuration
3. Add dedicated expansion logic for competitor, regulatory, and GTM analysis queries
4. Emit planning rationale so the API can explain why certain symbols and terms were chosen

## Related Docs

- `SEMANTIC_SEARCH_MODULE.md`
- `API_INTEGRATION_STATUS.md`
