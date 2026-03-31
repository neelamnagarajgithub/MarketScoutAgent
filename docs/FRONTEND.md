# MarketScout Frontend Documentation

## Overview

MarketScout Frontend is a modern, chat-style web interface built with **Next.js 14** and **React 18**. It provides an interactive experience for users to query the market intelligence backend, track analysis progress through distinct pipeline stages, and download generated PDF reports.

The frontend implements a ChatGPT-like UI pattern with a collapsible sidebar for conversation history, real-time progress indicators, and seamless PDF management.

## Technology Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Next.js** | 14.2.18 | React framework for production applications |
| **React** | 18.3.1 | UI library for component-based development |
| **React DOM** | 18.3.1 | React rendering for the browser |
| **CSS** | Custom | Dark-themed design system with CSS variables |

## Project Structure

```
Frontend/
├── app/                          # Next.js App Router directory
│   ├── api/
│   │   └── analyze/
│   │       └── route.js         # Backend proxy endpoint
│   ├── layout.js                # Root layout component
│   ├── page.js                  # Main chat interface
│   └── globals.css              # Global CSS + design tokens
├── public/                       # Static assets
│   ├── favicon.ico
│   ├── logo_*.png               # Brand logos (various formats)
│   └── logo_animation.mp4       # Animated AI orb
├── jsconfig.json                # JavaScript configuration
├── next.config.js               # Next.js configuration
├── package.json                 # Dependencies and scripts
├── .env.local.example           # Environment variable template
└── README.md                    # Setup instructions
```

## File Descriptions

### [layout.js](Frontend/app/layout.js)

Root layout component for the application.

**Responsibilities:**
- Sets page metadata (title, description, icons)
- Configures favicon and apple touch icons from public assets
- Wraps child components with HTML structure

**Key Exports:**
```typescript
metadata {
  title: "Scout AI"
  description: "Chat-style interface for market intelligence"
  icons: {
    icon: [logo_nobg.png, logo_whitebg.png]
    shortcut: logo_nobg.png
    apple: logo_whitebg.png
  }
}

RootLayout(children) → JSX
```

### [page.js](Frontend/app/page.js) - Main Interface

The primary chat interface component. This is a "use client" component using React hooks for state management.

**Key Features:**
- Chat-style message display
- Collapsible history sidebar with search
- Real-time analysis progress tracking (4 stages)
- PDF download functionality
- Query suggestions
- LocalStorage persistence for chat history

**State Hooks:**
```javascript
const [sidebarOpen, setSidebarOpen] = useState(true)
const [input, setInput] = useState("")                    // Query input
const [messages, setMessages] = useState([])              // All messages
const [isSending, setIsSending] = useState(false)         // Sending state
const [phaseIndex, setPhaseIndex] = useState(0)           // Current stage
const [searchQuery, setSearchQuery] = useState("")        // Search filter
const [searchOpen, setSearchOpen] = useState(false)       // Search UI toggle

// Refs for direct DOM access
const chatEndRef = useRef(null)                          // Auto-scroll anchor
const textareaRef = useRef(null)                         // Input resizing
const searchInputRef = useRef(null)                      // Search focus
```

**Message Structure:**
```javascript
// User message
{
  id: string,                 // unique: `${Date.now()}_${random}`
  role: "user",
  query: string,              // user's text input
  createdAt: ISO8601 timestamp
}

// Assistant message
{
  id: string,
  role: "assistant",
  query: string,              // echoed from user message
  status: "success" | "failed",
  successText: string,        // custom status label
  payload: object,            // full backend response
  pdfUrl: string | null,      // extracted PDF URL
  phaseIndex: 0-3,            // last completed stage
  createdAt: ISO8601 timestamp
}
```

**Analysis Phases (PHASES array):**
```javascript
[
  "Retrieving data from multiple sources",  // Phase 0
  "Judging the data",                       // Phase 1
  "Analyzing the data",                     // Phase 2
  "Generating report"                       // Phase 3
]
```

Each phase advances every 5.5 seconds (STAGE_DELAY_MS).

**Key Functions:**

#### `handleSend()`
- Validates query input
- Creates user message
- Triggers stage animation (5.5s × 4 phases = ~22 seconds)
- Calls `/api/analyze` endpoint
- Parses backend response
- Creates assistant message with status

#### `handleDownload(pdfUrl)`
- Fetches PDF from URL
- Creates blob download link
- Fallback: opens PDF in new tab if download fails

#### `advanceThroughStages(control)`
- Animates through 4 phases with delays
- Cancellable via `control.cancelled`
- Updates `phaseIndex` state

#### `historyItems` (useMemo)
- Groups messages into user-assistant pairs
- Filters based on search query
- Extracts PDF URLs for each pair

**Suggestions Array:**
```javascript
[
  "Nvidia AI chip market analysis 2025",
  "Top funded AI startups — Q1 2026",
  "Tesla vs BYD competitive landscape",
  "Enterprise SaaS market trends 2025",
  "Anthropic vs OpenAI strategy deep-dive"
]
```

**UI Sections:**
1. **Sidebar** - Collapsible history with search
2. **Chat Area** - Message display with auto-scroll
3. **Hero** - Welcome screen with suggestions (empty state)
4. **Composer** - Input textarea with send button
5. **Analysis Cards** - Status, phases, and results

**LocalStorage:**
- Key: `marketscout_history`
- Format: JSON array of messages
- Auto-saves on message change
- Auto-loads on component mount

### [AnalysisStatusCard Component](Frontend/app/page.js#L155)

Renders the analysis result card with progress, findings, and PDF download button.

**Props:**
```typescript
interface AnalysisStatusCardProps {
  msg: {
    status: "success" | "failed"
    payload: object
    pdfUrl?: string
    successText?: string
    phaseIndex?: number
  }
  onDownload: (pdfUrl: string) => void
  activePhaseIndex?: number    // for streaming UI
  isStreaming?: boolean        // shows live animation
}
```

**Features:**
- Animated AI orb (`.ai-orb.live` when streaming)
- Phase progress indicators
- Report summary and sections
- Key findings, risks, recommendations, competitive landscape
- Filters out "filler" placeholder text
- PDF download button (only on success)

**Report Sections Rendered:**
```javascript
REPORT_SECTIONS = [
  { key: "key_findings", label: "Key Findings", src: "report" },
  { key: "competitive_landscape", label: "Competitive Landscape", src: "sections" },
  { key: "risks", label: "Risks", src: "report" },
  { key: "recommendations", label: "Recommendations", src: "report" },
  { key: "decision_ready_next_steps", label: "Next Steps", src: "sections" }
]
```

### [api/analyze/route.js](Frontend/app/api/analyze/route.js) - Proxy Endpoint

Backend API proxy that forwards requests from the frontend to the backend service.

**Endpoint:** `POST /api/analyze`

**Function:**
```typescript
POST /api/analyze
Body: { query: string, user_id?: string }
Response: {
  query: string
  status: "success" | "failed"
  response: {
    status: string
    query: string
    pdf_link: string | null
    report: Report
    analysis_mode: "llm" | "fallback"
    falback_reason: string | null
    sources_count: number
    documents_count: number
    report_id: string
  }
  pdf_url?: string
  report_id: string
  timestamp: string
}
```

**Configuration:**
- Backend URL from env var: `BACKEND_ANALYZE_URL`
- Default fallback: `http://localhost:8000/v1/analyze`
- Mock response available for development

**Error Handling:**
- Catches JSON parse errors
- Returns structured error response
- Preserves backend error messages

## Environment Configuration

### `.env.local` File

```bash
# Backend analyze endpoint
BACKEND_ANALYZE_URL=http://localhost:8000/v1/analyze
```

**Setup:**
1. Copy `.env.local.example` to `.env.local`
2. Update `BACKEND_ANALYZE_URL` to match backend server
3. For local development: `http://localhost:8000/v1/analyze`

## Design System

### Color Palette (CSS Variables)

```css
:root {
  --bg: #212121;           /* Main background */
  --panel: #171717;        /* Primary panel/card */
  --panel-2: #262626;      /* Secondary panel */
  --panel-3: #2f2f2f;      /* Tertiary panel */
  --line: #353535;         /* Subtle divider */
  --line-strong: #454545;  /* Strong divider */
  --ink: #ececec;          /* Primary text */
  --ink-soft: #a7a7a7;     /* Secondary text */
  --success: #7ff2c3;      /* Success indicator (mint green) */
  --danger: #ff9b9b;       /* Error indicator (light red) */
  --shadow: 0 14px 26px rgba(0, 0, 0, 0.35);
}
```

### Typography

- **Font Family:** Manrope (400, 500, 600, 700, 800 weights)
- **Fallback Stack:** Avenir Next, Segoe UI, sans-serif
- **Source:** Google Fonts CDN

### Component Styles

#### Sidebar
- **Width:** 260px (open) / 68px (closed)
- **Transition:** 220ms ease
- **Z-Index:** 30 (fixed positioning)
- **Border:** Right border 1px solid #2b2b2b

#### Icons
- **Size:** 16px-18px (typical)
- **Stroke Width:** 1.8px
- **Color:** currentColor (inherits from text)

#### Buttons
- **Border Radius:** 8px-10px
- **Hover State:** lighter background + border
- **Disabled State:** reduced opacity

#### Analysis Card
- **Status Badges:** "Ready" (success), "Failed" (failed), "In progress" (working)
- **Phase Indicators:** Numbered dots with labels
- **PDF Button:** Download button (success only)

## Scripts

### Development

```bash
npm run dev
```
- Starts Next.js dev server
- Runs on `http://localhost:3000` by default
- Hot module replacement enabled
- Backend must be running on configured URL

### Production Build

```bash
npm run build
```
- Optimizes and bundles application
- Creates `.next/` directory

### Production Start

```bash
npm start
```
- Starts production server
- Requires `npm run build` first

### Linting

```bash
npm run lint
```
- Runs Next.js ESLint
- Checks for code quality issues

## Data Flow

### Query to Analysis

```
User Input
    ↓
[handleSend] validates query
    ↓
Create User Message
    ↓
Add to messages state
    ↓
Start phase animation
    ↓
POST to /api/analyze
    ↓
[Backend processes asynchronously]
    ↓
Response received
    ↓
Parse JSON
    ↓
Extract PDF URL
    ↓
Create Assistant Message
    ↓
Add to messages state
    ↓
Save to localStorage
    ↓
Display Analysis Card
```

### LocalStorage Persistence

```
On componentMount
    ↓
Load "marketscout_history"
    ↓
Parse JSON array
    ↓
Set messages state

On messages change
    ↓
Serialize to JSON
    ↓
Save to "marketscout_history"
```

## Performance Optimizations

1. **useMemo:** History items computed only when messages or searchQuery change
2. **Textarea Resizing:** Dynamically adjusts height up to 220px max
3. **Auto-scroll:** Uses ref to scroll to latest message
4. **Phase Animation:** Cancellable via control object
5. **Lazy PDF Download:** Uses Blob URLs with cleanup

## Accessibility Features

- **ARIA Labels:** All interactive elements have `aria-label`
- **Semantic HTML:** `<main>`, `<aside>`, `<section>`, `<header>`
- **Icon Accessibility:** SVGs marked with `aria-hidden="true"`
- **Focus Management:** Search input receives focus when opened
- **Keyboard Navigation:** Enter key sends message (Shift+Enter = newline)

## Browser Compatibility

- **Modern browsers:** Chrome, Firefox, Safari, Edge (latest versions)
- **Requires:** ES2020+ JavaScript support
- **Mobile:** Responsive design with hamburger menu toggle

## Usage Examples

### Basic Setup & Run

```bash
# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local
# Edit .env.local if backend is not on localhost:8000

# Start dev server
npm run dev

# Open browser
open http://localhost:3000
```

### Deploying to Production

```bash
# Build for production
npm run build

# Test production build locally
npm start

# Deploy .next/ directory and node_modules to hosting
```

### Customizing Suggestions

Edit the `SUGGESTIONS` array in [page.js](Frontend/app/page.js#L24) to add/remove query suggestions:

```javascript
const SUGGESTIONS = [
  "Your custom query 1",
  "Your custom query 2",
  // etc.
];
```

### Adjusting Phase Timeline

To change animation speed, edit `STAGE_DELAY_MS` in [page.js](Frontend/app/page.js#L17):

```javascript
const STAGE_DELAY_MS = 5500;  // milliseconds per phase
```

### Adding Report Sections

Edit `REPORT_SECTIONS` in [page.js](Frontend/app/page.js#L106) to display different report fields:

```javascript
const REPORT_SECTIONS = [
  { key: "your_field", label: "Display Label", src: "report" | "sections" },
]
```

## Troubleshooting

### Backend Not Responding

**Error:** "Backend returned an invalid JSON response"

**Solution:** 
1. Verify backend is running on configured URL
2. Check `BACKEND_ANALYZE_URL` in `.env.local`
3. Ensure backend CORS allows requests from `http://localhost:3000`

### Analysis Never Completes

**Issue:** Phase animation runs but no response received

**Solution:**
1. Check browser network tab for failed requests
2. Verify backend service is healthy
3. Increase backend timeout if processing large queries

### PDF Download Not Working

**Issue:** URL opens in new tab instead of downloading

**Solution:**
- This is expected browser behavior for cross-origin PDFs
- Manual download from new tab is fallback behavior
- Ensure `pdf_url` is passed from backend response

### LocalStorage Not Persisting

**Issue:** Chat history lost on page reload

**Solution:**
1. Check browser privacy settings (not in private/incognito mode)
2. Verify localStorage is not blocked by extensions
3. Check browser console for quota exceeded errors

## Related Documentation

- [ORCHESTRATOR.md](docs/ORCHESTRATOR.md) - Backend orchestration logic
- [API_INTEGRATION_STATUS.md](docs/API_INTEGRATION_STATUS.md) - Data source APIs
- [README.md](Frontend/README.md) - Quick start guide

## API Response Example

```json
{
  "query": "Nvidia AI chip market analysis 2025",
  "status": "success",
  "response": {
    "status": "success",
    "query": "Nvidia AI chip market analysis 2025",
    "pdf_link": "https://supabase.../reports/report_20260315_063925.pdf",
    "report": {
      "summary": "Nvidia dominates the AI chip market...",
      "key_findings": [
        "Finding 1",
        "Finding 2"
      ],
      "risks": [
        "Risk 1",
        "Risk 2"
      ],
      "recommendations": [
        "Recommendation 1"
      ],
      "confidence_score": 0.92,
      "sections": {
        "competitive_landscape": [
          "AMD gaining market share...",
          "Qualcomm focusing on edge..."
        ],
        "decision_ready_next_steps": [
          "Next step 1"
        ]
      }
    },
    "analysis_mode": "llm",
    "fallback_reason": null,
    "sources_count": 8,
    "documents_count": 45,
    "report_id": "uuid-string"
  },
  "pdf_url": "https://supabase.../reports/report_20260315_063925.pdf",
  "report_id": "uuid-string",
  "timestamp": "2025-03-31T12:34:56.789012"
}
```
