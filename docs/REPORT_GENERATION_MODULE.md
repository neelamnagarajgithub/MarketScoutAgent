# Report Generation Module

File: `app/pipeline/reporting.py`

## Purpose

`ReportGenerator` is the presentation layer of the pipeline. It converts the structured `AnalysisReport` into the final branded PDF artifact that is uploaded to Supabase and linked from the API response.

This stage is responsible for layout, branding, attribution, and PDF rendering safety. It is not responsible for creating or ranking the underlying analysis content.

## Position in the End-to-End Flow

1. Orchestrator calls `render_pdf(...)`
2. The PDF is rendered into a temporary local directory
3. `Database.upload_pdf_report(...)` uploads the file to Supabase storage
4. The temporary local file disappears when the request completes

This means the report module still writes a file during generation, but it is a transient rendering artifact rather than a retained local deliverable.

## Inputs and Output

Inputs:

- `query`
- `judged`
- `report`
- `out_dir`

Output:

- local path to the generated PDF, intended for immediate upload by the orchestrator

## Branding

Current branding behavior includes:

- product name `Scout AI`
- logo loaded from `utils/logo.png`
- branded cover/title block
- branded footer text on each page

This keeps the report self-identifying even outside the frontend.

## Rendering Stack

The module uses ReportLab primitives such as:

- `SimpleDocTemplate`
- `Paragraph`
- `Table`
- `ListFlowable`
- `PageBreak`
- `Image`

Typography and spacing are intentionally conservative to reduce PDF rendering edge cases.

## Document Structure

The final report generally includes:

1. branded title block and metadata
2. executive summary table
3. key findings
4. risks
5. recommendations
6. major strategic sections
7. evidence highlights table
8. bibliography table

Major strategic sections cover business context, market landscape, customer signals, competition, product implications, feature recommendations, GTM implications, strategic implications, opportunities, risks, and next steps.

## Citation Strategy

### Bibliography construction

`_collect_bibliography(judged)` builds a deduplicated reference list from judged evidence URLs.

Each entry includes:

- source
- title
- URL

### Index generation

`_source_index(...)` builds lookups for:

- URL to bibliography number
- source name to first bibliography number

### Citation formatting

`_citation_text(numbers)` formats references as bracket chains such as:

- `[1][4][12]`

### Section-level attribution

The current report uses section-level source attribution rather than citation spam on every bullet line.

That means:

- bullet lists remain readable
- a single `Section Sources:` line appears after a section when references exist

This was intentionally chosen for readability.

## Evidence Highlights Section

The evidence-highlights table is a compact audit trail between the analysis and the underlying evidence.

Each row contains:

- title
- source
- why it matters

This section helps readers quickly inspect the supporting evidence behind the synthesized narrative.

## PDF Safety and Glyph Handling

The PDF layer historically suffered from Unicode glyph issues, especially unsupported characters rendering as black squares.

`_safe_text(...)` hardens text by applying:

1. Unicode normalization
2. punctuation translation into ASCII-safe equivalents
3. removal of invisible Unicode characters
4. removal of unsupported symbol categories
5. final ASCII-only hardening
6. XML escaping for ReportLab paragraph safety
7. soft-wrap handling for long tokens and URLs

This is the main defense against rendering artifacts and paragraph-parser failures.

## Links and Bibliography URLs

`_link_p(url, style)` renders bibliography URLs as clickable links using ReportLab link markup.

That makes the bibliography both an attribution layer and a navigation aid.

## Relationship to Orchestrator and Storage

`ReportGenerator` only renders the file. It does not upload it and does not control retention.

Upload and retention behavior belong to:

- `app/orchestrator.py`
- `app/db.py`

Current behavior is remote-first:

- render locally to a temporary directory
- upload to Supabase storage
- discard the local temporary file

## Related Docs

- `ANALYSIS_MODULE.md`
- `API_INTEGRATION_STATUS.md`
