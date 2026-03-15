# API Integration Status

This document describes the current external-provider surface area of the market-intelligence pipeline. It is aligned to the current code in `app/simple_semantic_search.py`, `app/api_validator.py`, `app/fetchers/`, and `config.yaml`.

## Why This Document Exists

The system depends on many third-party providers, but they do not all play the same role.

Some are:

- always-important core providers for mainstream queries
- optional enrichers for broader coverage
- scraper-backed or dynamic integrations that can fail more often
- validated services that may not be actively scheduled for every query type

This document clarifies what is actually wired into the runtime and how failures are handled.

## Provider Families

The search engine organizes providers into these retrieval families:

1. Search discovery
2. News intelligence
3. GitHub intelligence
4. Financial intelligence
5. Business intelligence
6. Social media
7. Community intelligence
8. Startup intelligence
9. Security intelligence

Each query activates only a subset of these families.

## Search Discovery

Current primary provider:

- `serpapi`

Supplementary security-style discovery:

- `shodan`

Notes:

- SerpAPI is the main general web-search discovery source in the current runtime
- Bing and Google Custom Search are present in configuration shape but are not active in the current task builders

## News Intelligence

Actively supported providers:

- `newsapi`
- `gnews`
- `currents`
- `guardian`
- `nytimes`

Supplementary community/news crossover:

- Hacker News search scraping

Notes:

- Guardian and NYTimes are dynamically resolved and safely skipped if the expected fetcher symbol is absent
- News-family coverage is one of the most important contributors to report quality for broad market-analysis queries

## GitHub and Code Signals

Actively supported:

- GitHub PAT-backed organization repository fetch
- GitHub trending repository fetch

Notes:

- GitHub is treated as a product and engineering market signal, not only as a code host
- GitLab is integrated separately and appears in the business-intelligence family rather than a dedicated GitLab code family

## Financial Intelligence

Actively supported:

- `alpha_vantage`
- `massive`
- free/public Yahoo Finance path when helper exists

Notes:

- Alpha Vantage is used for both company overview and company-news style enrichment
- Massive is used for market/dividend-style data where supported
- financial-symbol generation is heavily influenced by the query optimizer

## Business Intelligence

Actively supported:

- `apollo`
- `gitlab`
- `shodan`

Notes:

- this family blends company, project, and infrastructure signals
- it is useful for competitor and company-analysis flows rather than broad market-trend queries

## Social and Community Intelligence

Actively supported:

- Reddit public JSON access
- Mastodon token-backed timeline access
- Stack Overflow public API
- Hacker News scraping path

Notes:

- Reddit is intentionally keyless in the current design
- community providers are lower-authority than financial/news providers, but they add important demand, sentiment, and developer-signal context

## Startup Intelligence

Supported sources include:

- startup tracker
- AngelList scraping path
- Crunchbase-news scraping path
- TechCrunch startup feed/path

Notes:

- these providers are useful for funding and emerging-company discovery
- some are inherently more fragile because they are scraper-backed or custom integrations

## Security Intelligence

Supported source:

- `shodan`

Notes:

- only relevant for certain query types
- used as optional enrichment rather than universal retrieval

## Validation Strategy

`APIKeyValidator` validates both keyed and free providers before the main search execution begins.

### Keyed providers checked

- `serpapi`
- `shodan`
- `newsapi`
- `gnews`
- `currents`
- `guardian`
- `nytimes`
- `github_pat`
- `gitlab`
- `apollo`
- `alpha_vantage`
- `massive`
- `mastodon`

### Free/public providers checked

- `hackernews`
- `yahoo_finance`
- `reddit`
- `npm_registry`
- `pypi`
- `stackoverflow`
- `coingecko`

### Storage/backend check

- Supabase REST accessibility is checked separately from search providers

## Runtime Failure Model

Third-party providers are expected to fail intermittently. Common causes include:

- invalid/expired keys
- upstream rate limits
- provider quota exhaustion
- temporary provider outage
- schema drift in scraper-backed sources

The runtime is designed around partial success, not all-or-nothing execution.

Protection mechanisms:

- provider validation before search execution
- safe task registration for optional fetchers
- `asyncio.gather(..., return_exceptions=True)`
- per-result normalization guarded by `try/except`

## What “Integrated” Means in This Repo

This repo supports more providers than it uses on every single request.

The correct interpretation is:

- the codebase contains a broad provider surface area
- only a subset is scheduled for any given query
- actual runtime usage depends on query type, configured keys, and source health

That is a healthier and more accurate model than claiming every configured service is always active.

## Most Important Providers for Reliable Output

If only a subset of services can be kept healthy, prioritize:

1. `serpapi`
2. `newsapi`
3. `gnews`
4. `alpha_vantage`
5. `github_personal_access_token`
6. Supabase database and storage access

Those have outsized influence on analysis quality for mainstream business and market queries.

## Related Docs

- `SEMANTIC_SEARCH_MODULE.md`
- `OPTIMIZER_INTEGRATION.md`
