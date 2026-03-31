# IntelligenceOrchestrator Module

## Overview

The `IntelligenceOrchestrator` class manages the complete pipeline for market intelligence analysis. It follows a sequential workflow: **retrieve → judge → analyze → report → store**.

This module serves as the central coordinator that orchestrates data retrieval, quality assessment, AI-powered analysis, PDF report generation, and persistent storage.

## Architecture

```
User Query
    ↓
[Retrieval]     → SimpleSemanticSearch.comprehensive_search()
    ↓
[Judgment]      → LLMJudge.judge() - Quality & relevance assessment
    ↓
[Analysis]      → AnalyzerAgent.analyze() - Insight extraction
    ↓
[Report Gen]    → ReportGenerator.render_pdf() - PDF creation
    ↓
[Storage]       → Database.save_analysis_report() & upload_pdf_report()
    ↓
Response Object with Report ID & PDF URL
```

## Module Location

- **File**: `app/orchestrator.py`
- **Package**: `app`
- **Dependencies**: Database, SimpleSemanticSearch, AnalyzerAgent, LLMJudge, ReportGenerator

## Class: IntelligenceOrchestrator

### Purpose
Coordinates the entire intelligence pipeline in a sequential manner, handling data flow and error management across multiple stages.

### Initialization

```python
orchestrator = IntelligenceOrchestrator(config_path: str = "config.yaml")
```

#### Parameters
- **config_path** (str, optional): Path to YAML configuration file. Defaults to `config.yaml`.

#### Initialization Process

1. **Load Configuration**
   - Reads YAML config file
   - Parses configuration dictionary

2. **Initialize Components**
   - `Database`: Manages Supabase connection and report storage
   - `SimpleSemanticSearch`: Handles multi-source data retrieval
   - `ReportGenerator`: Creates PDF reports

3. **Setup API Keys**
   - Prioritizes environment variables: `GOOGLE_API_KEY`, `GEMINI_API_KEY`
   - Falls back to config file keys: `GOOGLE_API_KEY`, `google_api_key`, `gemini_api_key`, `google_genai_api_key`
   - Logs warning if no key configured; components run in heuristic/fallback mode

4. **Initialize AI Agents**
   - `LLMJudge`: LLM-based quality assessment
   - `AnalyzerAgent`: LLM-based analysis engine

### Attributes

| Attribute | Type | Purpose |
|-----------|------|---------|
| `config` | dict | Configuration loaded from YAML |
| `db` | Database | Database interface for persistence |
| `search_engine` | SimpleSemanticSearch | Multi-source data retrieval |
| `reporter` | ReportGenerator | PDF report generation |
| `judge` | LLMJudge | Quality assessment agent |
| `analyzer` | AnalyzerAgent | Analysis and insight extraction |

### Methods

#### `async run(query: str, user_id: Optional[str] = None) -> Dict[str, Any]`

Executes the complete intelligence pipeline for a given query.

**Parameters:**
- **query** (str): User's market intelligence query
- **user_id** (str, optional): Identifier for query attribution and organization

**Returns:** Dictionary containing:
```python
{
    "query": str,              # Original query
    "status": "success",       # Operation status
    "response": {              # Main response object
        "status": "success",
        "query": str,
        "pdf_link": str | None,    # Supabase PDF URL
        "report": {                # Structured report data
            "summary": str,
            "key_findings": list,
            "risks": list,
            "recommendations": list,
            "confidence_score": float,
            "sections": dict,
        },
        "analysis_mode": str,      # "llm" or "fallback"
        "fallback_reason": str | None,  # Reason if fallback used
        "sources_count": int,      # Number of unique sources
        "documents_count": int,    # Total documents retrieved
        "report_id": str,          # Database record ID
    },
    "pdf_url": str | None,         # Same as response.pdf_link
    "report_id": str,              # Database record ID
    "timestamp": str,              # ISO 8601 timestamp
}
```

**Pipeline Stages:**

1. **Stage 1: Retrieval**
   ```python
   raw = await self.search_engine.comprehensive_search(query)
   ```
   - Searches multiple data sources (APIs, web, etc.)
   - Returns raw search results with metadata

2. **Stage 2: Judgment**
   ```python
   judged = await self.judge.judge(query, raw)
   ```
   - Filters results based on quality and relevance
   - Adds guardrail assessments
   - Produces judged_results with confidence scores

3. **Stage 3: Analysis**
   ```python
   analyzed = await self.analyzer.analyze(judged)
   ```
   - Extracts key findings, risks, recommendations
   - Generates summary and confidence scores
   - Structures sections for report generation
   - Fallback mode: runs heuristic analysis if API unavailable

4. **Stage 4: Report Generation**
   ```python
   with tempfile.TemporaryDirectory(prefix="scoutai_report_") as temp_dir:
       pdf_local = self.reporter.render_pdf(query, judged, analyzed, out_dir=temp_dir)
   ```
   - Creates temporary directory for PDF storage
   - Renders PDF with all analysis sections
   - Cleans up temporary files automatically

5. **Stage 5: Storage**
   ```python
   await self.db.init_models()
   uploaded = await self.db.upload_pdf_report(pdf_local, bucket="reports")
   report_id = await self.db.save_analysis_report(...)
   ```
   - Initializes database models (Supabase setup)
   - Uploads PDF to cloud storage
   - Saves analysis report metadata to database
   - Returns Supabase URL if upload successful

6. **Stage 6: Response Assembly**
   - Extracts analysis insights
   - Detects analysis mode (LLM vs fallback)
   - Counts sources and documents
   - Constructs final response payload

**Error Handling:**
- Graceful degradation to fallback/heuristic mode if API keys missing
- Safe navigation for nested dictionary access (e.g., `dict.get()` with defaults)
- Temporary file cleanup via context manager
- Optional PDF upload (frontend compatibility maintained)

**Async Execution:**
- Method is async; use `await` or `asyncio.run()`
- Allows concurrent processing across stages
- Non-blocking database operations

## Configuration

The orchestrator requires a `config.yaml` file with:

```yaml
keys:
  google_api_key: "your-api-key"        # Optional: GEMINI API key
  GEMINI_API_KEY: "your-api-key"        # Alternative config key

# Plus Database config for Supabase connection
```

**Environment Variable Precedence:**
1. `GOOGLE_API_KEY` environment variable
2. `GEMINI_API_KEY` environment variable
3. `keys.GOOGLE_API_KEY` from config
4. `keys.google_api_key` from config
5. `keys.gemini_api_key` from config
6. `keys.google_genai_api_key` from config

## Response Structure

### Success Response Example

```json
{
  "query": "market trends in AI chips",
  "status": "success",
  "response": {
    "status": "success",
    "query": "market trends in AI chips",
    "pdf_link": "https://supabase.../reports/report-id.pdf",
    "report": {
      "summary": "The AI chip market is growing...",
      "key_findings": ["Finding 1", "Finding 2"],
      "risks": ["Risk 1"],
      "recommendations": ["Rec 1"],
      "confidence_score": 0.92,
      "sections": {
        "source_breakdown": {
          "source_counts": {"source1": 5, "source2": 3}
        },
        "guardrail_summary": {
          "judge_notes": [...]
        }
      }
    },
    "analysis_mode": "llm",
    "fallback_reason": null,
    "sources_count": 2,
    "documents_count": 8,
    "report_id": "uuid-string"
  },
  "pdf_url": "https://supabase.../reports/report-id.pdf",
  "report_id": "uuid-string",
  "timestamp": "2025-03-31T12:34:56.789012"
}
```

## Analysis Modes

The orchestrator supports two analysis modes:

| Mode | Condition | Processing |
|------|-----------|-----------|
| **LLM** | Gemini API key available | Full AI-powered analysis with LLM judge |
| **Fallback** | No API key or API unavailable | Heuristic analysis based on data patterns |

Mode is determined post-analysis by checking for `analyzer_fallback_reason=` in judge notes.

## Data Flow

```
Input: query, user_id
  ↓
1. Retrieve raw documents from multiple sources
  ↓
2. Judge documents for quality and relevance
  ↓
3. Analyze with LLM (or fallback heuristics)
  ↓
4. Structure insights (findings, risks, recommendations)
  ↓
5. Generate PDF report
  ↓
6. Upload PDF to Supabase storage
  ↓
7. Save report metadata to database
  ↓
Output: response with report_id, pdf_url, analysis results
```

## Dependencies

| Module | Purpose |
|--------|---------|
| `app.db.Database` | Supabase connection and report persistence |
| `app.simple_semantic_search.SimpleSemanticSearch` | Multi-source data retrieval |
| `app.pipeline.analyzer.AnalyzerAgent` | AI analysis and insight extraction |
| `app.pipeline.llm_judge.LLMJudge` | Quality assessment and filtering |
| `app.pipeline.reporting.ReportGenerator` | PDF report generation |

## Usage Examples

### Basic Usage

```python
from app.orchestrator import IntelligenceOrchestrator
import asyncio

async def main():
    orchestrator = IntelligenceOrchestrator("config.yaml")
    result = await orchestrator.run("Market trends in AI chips")
    print(f"Report ID: {result['report_id']}")
    print(f"PDF URL: {result['pdf_url']}")

asyncio.run(main())
```

### With User ID for Attribution

```python
result = await orchestrator.run(
    query="Enterprise software market analysis",
    user_id="user-123"
)
```

### Accessing Report Insights

```python
report = result['response']['report']
print(f"Summary: {report['summary']}")
print(f"Confidence: {report['confidence_score']}")
print(f"Key Findings: {report['key_findings']}")
print(f"Analysis Mode: {result['response']['analysis_mode']}")
```

## Performance Considerations

1. **Sequential Processing**: Stages execute in order; cannot parallelize across judge→analyze→report
2. **Database Initialization**: `db.init_models()` called each run; consider caching in production
3. **Temporary Files**: Cleaned up automatically via context manager
4. **PDF Upload**: Non-blocking async operation; falls back to local availability if upload fails
5. **API Calls**: Gracefully degrades if Gemini API unavailable

## Error Handling & Resilience

- **Missing API Keys**: Logged as warning; analysis continues in fallback mode
- **Missing Config**: Will raise `FileNotFoundError` if config.yaml not found
- **Safe Dictionary Access**: All nested dict access uses `.get()` with defaults
- **Async Safety**: All database operations are async-safe
- **PDF Upload Failure**: Falls back to local storage; frontend maintains compatibility

## Logging

The module uses Python's standard logging. Configure as:

```python
import logging
logging.basicConfig(level=logging.INFO)
# Warnings logged when API keys missing
```

## Related Documentation

- [DETAILED_ARCHITECTURE.md](DETAILED_ARCHITECTURE.md) - Full system architecture
- [GUARDRAIL_AND_LLM_JUDGE.md](GUARDRAIL_AND_LLM_JUDGE.md) - Judge implementation
- [ANALYSIS_MODULE.md](ANALYSIS_MODULE.md) - Analyzer implementation
- [REPORT_GENERATION_MODULE.md](REPORT_GENERATION_MODULE.md) - Report generation
- [SEMANTIC_SEARCH_MODULE.md](SEMANTIC_SEARCH_MODULE.md) - Data retrieval
