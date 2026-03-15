# MarketScout Frontend (Next.js)

Chat-style UI for the MarketScout backend.

## Run locally

1. Copy `.env.local.example` to `.env.local`.
2. Confirm backend URL in `.env.local`:
   - `BACKEND_ANALYZE_URL=http://localhost:8000/v1/analyze`
3. Install dependencies:
   - `npm install`
4. Start dev server:
   - `npm run dev`
5. Open:
   - `http://localhost:3000`

## Features

- ChatGPT-like chat layout
- Collapsible history sidebar using hamburger icon
- Query input + send flow
- In-flight status phases:
  - Analysing
  - Gathering resources
  - Generating PDF
  - Success state shown when backend returns
- PDF download button when `pdf_url` is present
- Raw backend response rendering
