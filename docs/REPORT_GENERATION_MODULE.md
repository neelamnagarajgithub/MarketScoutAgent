# Report Generation Module

File: `app/pipeline/reporting.py`

## Purpose

`ReportGenerator` transforms `AnalysisReport` + `JudgedDataset` into a professional PDF artifact with:

- Structured sections
- Bulleted findings/risks/recommendations
- Evidence highlights table
- Numbered bibliography with clickable links
- Inline numeric citations in section content

## Inputs

- `query: str`
- `judged: JudgedDataset`
- `report: AnalysisReport`
- `out_dir` (default `search_results`)

Output:

- Path to generated PDF file

## Rendering Stack

- ReportLab (`SimpleDocTemplate`, `Paragraph`, `Table`, `ListFlowable`, `PageBreak`)
- Helvetica-based typography for broad compatibility
- Custom header/footer per page

## Citation System

### Bibliography Collection

`_collect_bibliography(judged)`:

- Deduplicates URLs
- Keeps source + title + URL rows
- Sorts deterministically

### Source Index

`_source_index(bibliography)` builds:

- `by_url`: URL -> reference number
- `by_source`: source name -> first reference number

### Inline Citation Formatting

`_citation_text(numbers)` returns bracket style references such as:

- `[1][11][48]`

### Section Citation Inference

`_section_citations(section_name, evidence, source_idx)`:

- Uses section-to-source preference rules
- Augments with evidence URLs/sources
- Produces small citation sets per section

## Glyph and Text Safety

### `_safe_text(text)`

This is the key method for preventing PDF parser and font rendering issues.

Safety pipeline includes:

1. Unicode normalization (`NFKC`)
2. Character translation of problematic punctuation to ASCII
3. Removal of known square/replacement glyph ranges
4. Removal of zero-width and unsupported symbol classes
5. Final ASCII hardening to avoid Helvetica black-box artifacts
6. XML escaping for ReportLab paragraph parser
7. Soft-wrap insertion for long tokens/URLs

This is the primary defense against artifacts like:

- `e■g■`
- `3.■5`
- `go■to■market`

## Document Sections

Rendered order includes:

1. Title and run metadata
2. Executive summary block
3. Key findings
4. Risks
5. Recommendations
6. Named strategic sections from `report.sections`
7. Evidence highlights table
8. Bibliography table (`#`, source, title, URL)

## Link Activation

`_link_p(url, style)` renders URL cells as clickable links in the final PDF using ReportLab `<link>` tags.

## Pagination and Layout

- Automatic page breaks for long sections
- Repeat headers in tables where configured
- Compact paddings to maximize signal density

## Extension Ideas

Potential next improvements:

- Sentence-level evidence-to-claim mapping
- Source credibility scoring in bibliography
- Optional executive one-page summary mode
- Themed report templates by query type
