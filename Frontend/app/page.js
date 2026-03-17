"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const PHASES = [
  "Retrieving data from multiple sources",
  "Judging the data",
  "Analyzing the data",
  "Generating report"
];

const STAGE_DELAY_MS = 5500;

const SUGGESTIONS = [
  "Nvidia AI chip market analysis 2025",
  "Top funded AI startups — Q1 2026",
  "Tesla vs BYD competitive landscape",
  "Enterprise SaaS market trends 2025",
  "Anthropic vs OpenAI strategy deep-dive",
];



function SidebarIcon({ icon }) {
  if (icon === "edit") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 20h9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M16.5 3.5a2.12 2.12 0 1 1 3 3L7 19l-4 1 1-4 12.5-12.5z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (icon === "search") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
        <path d="m20 20-3.6-3.6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }

  if (icon === "image") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="1.8" />
        <circle cx="9" cy="10" r="1.6" fill="currentColor" />
        <path d="m6 17 4-4 3 3 2-2 3 3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }

  if (icon === "apps") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="4" y="4" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8" />
        <rect x="13" y="4" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8" />
        <rect x="4" y="13" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8" />
        <rect x="13" y="13" width="7" height="7" rx="1.6" stroke="currentColor" strokeWidth="1.8" />
      </svg>
    );
  }

  if (icon === "research") {
    return (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 3.5 19.8 7v10L12 20.5 4.2 17V7L12 3.5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
        <path d="m12 8 4.3 2.2V15L12 17.2 7.7 15v-4.8L12 8Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      </svg>
    );
  }

  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M8 7h8M8 12h8M8 17h8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <rect x="3" y="4" width="18" height="16" rx="3" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}

function makeId() {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function getPdfUrl(payload) {
  return (
    payload?.pdf_url ||
    payload?.response?.pdf_url ||
    payload?.response?.pdf_link ||
    null
  );
}

function getSuccessText(payload) {
  const pdfUrl = getPdfUrl(payload);
  if (pdfUrl) {
    return "Report generated";
  }
  return "Analysis completed. PDF URL not present in response.";
}

const REPORT_SECTIONS = [
  { key: "key_findings", label: "Key Findings", src: "report" },
  { key: "competitive_landscape", label: "Competitive Landscape", src: "sections" },
  { key: "risks", label: "Risks", src: "report" },
  { key: "recommendations", label: "Recommendations", src: "report" },
  { key: "decision_ready_next_steps", label: "Next Steps", src: "sections" }
];

const FILLER = new Set([
  "Expand this area with additional evidence-backed detail.",
  "Tie this point to measurable business or product impact.",
  "Clarify assumptions and validation path."
]);

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function formatTime(isoDate) {
  try {
    return new Date(isoDate).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    });
  } catch {
    return "";
  }
}

function AnalysisStatusCard({ msg, onDownload, activePhaseIndex = -1, isStreaming = false }) {
  const isSuccess = msg?.status === "success";
  const isFailed = msg?.status === "failed";
  const pdfUrl = msg?.pdfUrl;
  const statusText = msg?.successText || (isFailed ? "Analysis failed" : "Preparing report");
  const detail = msg?.payload?.detail || msg?.payload?.response?.detail || null;
  const phaseMarker = isStreaming ? activePhaseIndex : (msg?.phaseIndex ?? -1);
  const visiblePhases = PHASES.slice(0, Math.max(phaseMarker + 1, isStreaming ? 1 : 0));
  const report = msg?.payload?.response?.report;
  const sections = report?.sections;

  function getSectionItems(config) {
    const source = config.src === "report" ? report?.[config.key] : sections?.[config.key];
    if (!Array.isArray(source)) {
      return [];
    }
    return source.filter((item) => !FILLER.has(item));
  }

  return (
    <div className={`analysis-card${isSuccess ? " analysis-card-success" : ""}${isFailed ? " analysis-card-failed" : ""}`}>
      <div className={`ai-orb${isStreaming ? " live" : ""}`} aria-hidden="true">
        <video src="/logo_animation.mp4" autoPlay muted loop playsInline />
      </div>

      <div className="analysis-card-header">
        <div>
          <p className="analysis-card-kicker">MarketScout run</p>
          <h3 className="analysis-card-title">{statusText}</h3>
        </div>
        <span className={`analysis-badge ${isSuccess ? "ok" : isFailed ? "fail" : "working"}`}>
          {isSuccess ? "Ready" : isFailed ? "Failed" : "In progress"}
        </span>
      </div>

      <div className="analysis-stage-list">
        {visiblePhases.map((phase, idx) => {
          const isComplete = isSuccess ? idx <= phaseMarker : idx < phaseMarker;
          const isCurrent = isStreaming && idx === phaseMarker;

          return (
            <div key={phase} className={`analysis-stage${isComplete ? " complete" : ""}${isCurrent ? " current" : ""}`}>
              <span className="analysis-stage-dot" />
              <span className="analysis-stage-label">{phase}</span>
            </div>
          );
        })}
      </div>

      {isFailed && detail ? <p className="analysis-detail">{detail}</p> : null}

      {isSuccess && report ? (
        <div className="analysis-result">
          {report.summary ? <p className="analysis-summary">{report.summary}</p> : null}

          {REPORT_SECTIONS.map((config) => {
            const items = getSectionItems(config);
            if (!items.length) {
              return null;
            }

            return (
              <section key={config.key} className="analysis-result-section">
                <h4>{config.label}</h4>
                <ul>
                  {items.map((item, index) => (
                    <li key={`${config.key}_${index}`}>{item}</li>
                  ))}
                </ul>
              </section>
            );
          })}
        </div>
      ) : null}

      {isSuccess && pdfUrl ? (
        <div className="analysis-actions">
          <button className="download-btn download-btn-success" onClick={() => onDownload(pdfUrl)}>
            Download PDF
          </button>
        </div>
      ) : null}
    </div>
  );
}

export default function HomePage() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isSending, setIsSending] = useState(false);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const phaseIndexRef = useRef(0);
  const chatEndRef = useRef(null);
  const textareaRef = useRef(null);
  const searchInputRef = useRef(null);

  function resizeTextarea() {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 220)}px`;
  }

  useEffect(() => {
    const saved = localStorage.getItem("marketscout_history");
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          setMessages(parsed);
        }
      } catch {
        // ignore malformed local storage
      }
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("marketscout_history", JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending, phaseIndex]);

  useEffect(() => {
    resizeTextarea();
  }, [input]);

  const historyItems = useMemo(() => {
    const items = [];

    for (let index = 0; index < messages.length; index += 1) {
      const current = messages[index];
      if (current?.role !== "user") continue;

      let nextAssistant = null;
      for (let cursor = index + 1; cursor < messages.length; cursor += 1) {
        if (messages[cursor]?.role === "assistant") {
          nextAssistant = messages[cursor];
          break;
        }
      }

      items.push({
        id: current.id,
        query: current.query,
        createdAt: current.createdAt,
        pdfUrl: nextAssistant?.pdfUrl || null
      });
    }

    if (!searchQuery.trim()) return items;
    const query = searchQuery.toLowerCase();
    return items.filter((item) => item.query.toLowerCase().includes(query));
  }, [messages, searchQuery]);

  const isEmpty = messages.length === 0 && !isSending;

  function handleNewChat() {
    if (isSending) return;
    setMessages([]);
    setInput("");
    setSearchQuery("");
    setSearchOpen(false);
  }

  function toggleSearch() {
    setSearchOpen((v) => {
      if (!v) setTimeout(() => searchInputRef.current?.focus(), 50);
      else setSearchQuery("");
      return !v;
    });
  }

  async function advanceThroughStages(control) {
    phaseIndexRef.current = 0;
    setPhaseIndex(0);

    for (let index = 1; index < PHASES.length; index += 1) {
      if (control?.cancelled) break;
      await sleep(STAGE_DELAY_MS);
      if (control?.cancelled) break;
      phaseIndexRef.current = index;
      setPhaseIndex(index);
    }
  }

  async function handleSend() {
    const query = input.trim();
    if (!query || isSending) return;

    const userMessage = {
      id: makeId(),
      role: "user",
      query,
      createdAt: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    const stageControl = { cancelled: false };
    let stageSequence = Promise.resolve();

    try {
      stageSequence = advanceThroughStages(stageControl);
      const response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ query, user_id: "default-user" })
      });

      let payload;
      try {
        payload = await response.json();
      } catch {
        payload = {
          status: "failed",
          detail: "Backend returned an invalid JSON response"
        };
      }

      const status = payload?.status || (response.ok ? "success" : "failed");
      stageControl.cancelled = status === "failed";
      await stageSequence;

      const pdfUrl = getPdfUrl(payload);

      const assistantMessage = {
        id: makeId(),
        role: "assistant",
        query,
        status,
        successText:
          status === "success"
            ? getSuccessText(payload)
            : (payload?.detail || payload?.response?.detail || "Analysis failed"),
        payload,
        pdfUrl,
        phaseIndex: status === "failed" ? phaseIndexRef.current : PHASES.length - 1,
        createdAt: new Date().toISOString()
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      stageControl.cancelled = true;
      await stageSequence;
      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: "assistant",
          query,
          status: "failed",
          successText: "Request failed",
          payload: {
            status: "failed",
            detail: error?.message || "Unknown network error"
          },
          pdfUrl: null,
          phaseIndex: phaseIndexRef.current,
          createdAt: new Date().toISOString()
        }
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleDownload(pdfUrl) {
    if (!pdfUrl) return;

    try {
      const response = await fetch(pdfUrl);
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);

      const anchor = document.createElement("a");
      anchor.href = objectUrl;
      anchor.download = `market_report_${Date.now()}.pdf`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();

      URL.revokeObjectURL(objectUrl);
    } catch {
      window.open(pdfUrl, "_blank", "noopener,noreferrer");
    }
  }

  return (
    <main
      className="shell"
      style={{ "--sidebar-width": sidebarOpen ? "260px" : "68px" }}
    >
      <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`}>
        <div className="sidebar-head">
          {sidebarOpen ? (
            <div className="sidebar-top-row">
              <img src="/logo_nobg.png" alt="Scout AI" className="brand-logo" />
              <button
                className="icon-btn sidebar-toggle-btn"
                onClick={() => setSidebarOpen((v) => !v)}
                aria-label="Toggle history sidebar"
              >
                <span className="hamburger" />
              </button>
            </div>
          ) : null}

          {!sidebarOpen ? (
            <button
              className="icon-btn sidebar-toggle-btn"
              onClick={() => setSidebarOpen((v) => !v)}
              aria-label="Toggle history sidebar"
            >
              <span className="hamburger" />
            </button>
          ) : null}

          {sidebarOpen && (
            <div className="sidebar-actions">
              <button className="sidebar-action-btn" onClick={handleNewChat} title="New chat">
                {/* pencil-square icon */}
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                New chat
              </button>
              <button className="sidebar-action-btn" onClick={toggleSearch} title="Search chats">
                {/* search icon */}
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                </svg>
                Search chats
              </button>
            </div>
          )}
        </div>

        {sidebarOpen ? (
          <div className="sidebar-content">
            

            <div className="history-section-head">
              <p className="history-section-title">Your chats</p>
            </div>

            {searchOpen ? (
              <div className="sidebar-search sidebar-search-inline">
                <input
                  ref={searchInputRef}
                  type="text"
                  placeholder="Search history…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                {searchQuery ? (
                  <button className="search-clear" onClick={() => setSearchQuery("")} aria-label="Clear">
                    ×
                  </button>
                ) : null}
              </div>
            ) : null}

            <div className="history-list">
            {historyItems.length === 0 ? (
              <p className="muted">{searchQuery ? "No matches" : "No history yet"}</p>
            ) : (
              historyItems
                .slice()
                .reverse()
                .map((item) => (
                  <div key={item.id} className="history-card history-row">
                    <div className="history-copy">
                      <p>{item.query}</p>
                      <span>{formatTime(item.createdAt)}</span>
                    </div>
                    {item.pdfUrl ? (
                      <button
                        className="history-download-btn"
                        onClick={() => handleDownload(item.pdfUrl)}
                        aria-label={`Download PDF for ${item.query}`}
                        title="Download PDF"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                          <path
                            d="M12 3V15M12 15L7 10M12 15L17 10M5 19H19"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        </svg>
                      </button>
                    ) : null}
                  </div>
                ))
            )}
            </div>
          </div>
        ) : null}
      </aside>

      <section className="chat-area">
        <header className="chat-header">
          <button
            className="icon-btn mobile"
            onClick={() => setSidebarOpen((v) => !v)}
            aria-label="Open history"
          >
            <span className="hamburger" />
          </button>
          <button className="chat-model-btn" type="button" aria-label="Current model">
            <span className="chat-title">Scout AI</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </header>

        <div className={`messages${isEmpty ? " messages-empty" : ""}`}>
          {isEmpty ? (
            <div className="hero-center">
              <h1 className="hero-heading">What are you analyzing today?</h1>
              <div className="hero-composer-area">
                <div className="composer">
                  <textarea
                    ref={textareaRef}
                    placeholder="Ask about a company, market, or trend…"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSend();
                      }
                    }}
                    rows={1}
                  />
                  <button
                    className="send-arrow"
                    onClick={handleSend}
                    disabled={isSending || !input.trim()}
                    aria-label="Send query"
                    title="Send"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                      <path
                        d="M12 19V5M12 5L6 11M12 5L18 11"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                </div>
                <div className="suggestions-row">
                  {SUGGESTIONS.map((s) => (
                    <button key={s} className="suggestion-chip" onClick={() => setInput(s)}>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => {
                if (msg.role === "user") {
                  return (
                    <div key={msg.id} className="msg-row user">
                      <div className="bubble user">{msg.query}</div>
                    </div>
                  );
                }

                return (
                  <div key={msg.id} className="msg-row assistant">
                    <AnalysisStatusCard msg={msg} onDownload={handleDownload} />
                  </div>
                );
              })}

              {isSending ? (
                <div className="msg-row assistant">
                  <AnalysisStatusCard activePhaseIndex={phaseIndex} isStreaming onDownload={handleDownload} />
                </div>
              ) : null}

              <div ref={chatEndRef} />
            </>
          )}
        </div>

        {!isEmpty ? (
          <div className="composer-wrap">
            <div className="composer">
              <textarea
                ref={textareaRef}
                placeholder="Message MarketScout"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                rows={1}
              />
              <button
                className="send-arrow"
                onClick={handleSend}
                disabled={isSending || !input.trim()}
                aria-label="Send query"
                title="Send"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M12 19V5M12 5L6 11M12 5L18 11"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
