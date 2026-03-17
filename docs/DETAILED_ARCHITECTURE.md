# MarketScout Detailed Architecture

## 1. System Boundary

MarketScout is an API-first market-intelligence system with a chat frontend.
The runtime path for analysis is:

1. Frontend sends query to `POST /v1/analyze`.
2. Orchestrator runs `retrieve -> judge -> analyze -> report -> store`.
3. PDF is generated in a temporary directory, uploaded to Supabase Storage, and local temp files are removed.
4. Final response envelope is returned with analysis payload and remote `pdf_url`.

## 2. Component Architecture

```mermaid
flowchart LR
    subgraph Client
      FE[Next.js Frontend\nChat UI]
    end

    subgraph API
      MAIN[FastAPI app/main.py\nPOST /v1/analyze]
      ORCH[IntelligenceOrchestrator\napp/orchestrator.py]
    end

    subgraph Retrieval
      SEARCH[SimpleSemanticSearch\nTask planners + async fetch]
      FETCH[External Fetchers\nNews/Search/Finance/Social/Startup/Security]
      NORM[Normalizer + dedupe keys]
    end

    subgraph Evaluation
      GR[GuardrailEngine\nsanitize/filter/dedupe]
      JUDGE[LLMJudge\nheuristics + LLM keep/drop]
    end

    subgraph Analysis
      ANA[AnalyzerAgent\nGemini JSON-mode + repair + fallback]
    end

    subgraph Reporting
      PDF[ReportGenerator\nReportLab PDF]
    end

    subgraph Persistence
      DB[(Supabase Postgres\nanalysis_reports + documents)]
      STO[(Supabase Storage\nreports bucket)]
      SQLITE[(SQLite fallback)]
    end

    FE --> MAIN --> ORCH
    ORCH --> SEARCH --> FETCH
    FETCH --> NORM --> SEARCH
    SEARCH --> JUDGE
    JUDGE --> GR
    GR --> JUDGE
    JUDGE --> ANA --> PDF
    PDF --> STO
    ORCH --> DB
    DB -.fallback.-> SQLITE
    ORCH --> MAIN --> FE
```

## 3. Runtime Sequence (Detailed)

```mermaid
sequenceDiagram
    participant U as User
    participant FE as Frontend
    participant API as FastAPI /v1/analyze
    participant O as Orchestrator
    participant S as SimpleSemanticSearch
    participant J as LLMJudge + Guardrails
    participant A as AnalyzerAgent
    participant R as ReportGenerator
    participant D as Database
    participant B as Supabase Storage

    U->>FE: Submit query
    FE->>API: POST /v1/analyze {query, user_id}
    API->>O: run(query, user_id)

    O->>S: comprehensive_search(query)
    S->>S: Build task plan by source family
    S->>S: Execute async fetch tasks
    S->>S: Normalize and aggregate raw data
    S-->>O: raw search payload

    O->>J: judge(query, raw_results)
    J->>J: Guardrails enforce() (sanitize/filter/dedupe)
    J->>J: Heuristic relevance scoring
    J->>J: Optional LLM keep_indices validation
    J-->>O: JudgedDataset

    O->>A: analyze(JudgedDataset)
    A->>A: JSON-mode invoke (schema/mime attempts)
    A->>A: Parse -> compact retry -> repair retry
    A->>A: Quality gate + section normalization
    A-->>O: AnalysisReport

    O->>R: render_pdf(query, judged, analyzed, temp_dir)
    R-->>O: temp pdf path
    O->>D: init_models()
    O->>D: upload_pdf_report(temp_pdf, bucket=reports)
    D->>B: PUT report object
    B-->>D: remote URL
    D-->>O: uploaded pdf_url

    O->>D: save_analysis_report(query, response_json, pdf_url, user_id)
    D-->>O: report_id
    O-->>API: final envelope
    API-->>FE: AnalyzeResponse
    FE-->>U: Render report + download link
```

## 4. Data Contracts

### 4.1 Request Contract

- Endpoint: `POST /v1/analyze`
- Input (`AnalyzeRequest`):
  - `query: string`
  - `user_id: string | null`

### 4.2 Response Envelope

- Top-level:
  - `query`
  - `status`
  - `response` (normalized payload)
  - `pdf_url`
  - `report_id`
  - `timestamp`

- Nested analysis payload includes:
  - `summary`
  - `key_findings[]`
  - `risks[]`
  - `recommendations[]`
  - `confidence_score`
  - `sections{...}`
  - `analysis_mode` (`llm` or `fallback`)
  - `fallback_reason` (when applicable)

## 5. Reliability and Fallback Design

### 5.1 Retrieval/Judge Resilience

- Task builders safely skip unavailable integrations.
- Guardrails sanitize and remove low-signal or unsafe items.
- Judge combines heuristics with optional LLM validation.

### 5.2 Analyzer Resilience

- Primary generation uses JSON-constrained mode where supported.
- Parsing pipeline handles code fences, escaped JSON, malformed JSON repairs, and object extraction.
- Retry chain:
  1. full prompt parse
  2. compact prompt parse
  3. JSON repair call
  4. deterministic fallback report

### 5.3 Storage Resilience

- DB init order: Supabase -> PostgreSQL -> SQLite fallback.
- Report PDF is uploaded remotely; runtime local retention is disabled.

## 6. Persistence Model

### 6.1 `documents`

- Ingested and normalized evidence records with source/provider/content/metadata.

### 6.2 `analysis_reports`

- Query-centric report records with full response JSON and optional `pdf_url`.

## 7. Security and Guardrails

- Prompt injection and suspicious pattern detection in guardrails.
- Sensitive string redaction in text/metadata.
- URL sanity checks and content-quality thresholds.
- Report-facing guardrail summary keeps only high-level operational signals.

## 8. Operational Observability

- Logging at fetch, judge, analyzer, DB, and upload stages.
- Analyzer failures are encoded into `fallback_reason` and guardrail notes.
- Response always returns schema-normalized envelope from API layer.
