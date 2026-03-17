import os
import re
import unicodedata
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem, Table, TableStyle, PageBreak, Image
)
import html

from app.pipeline.types import AnalysisReport, JudgedDataset


class ReportGenerator:
    def _logo_path(self) -> str:
        # app/pipeline/reporting.py -> repo/utils/logo.png
        return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "utils", "logo.png"))

    def _source_index(self, bibliography: list) -> dict:
        index = {}
        source_first = {}
        for i, ref in enumerate(bibliography, start=1):
            url = (ref.get("url") or "").strip()
            src = (ref.get("source") or "unknown").strip().lower()
            if url:
                index[url] = i
            if src and src not in source_first:
                source_first[src] = i
        return {"by_url": index, "by_source": source_first}

    def _citation_text(self, numbers: list) -> str:
        nums = sorted({int(n) for n in numbers if isinstance(n, int) and n > 0})
        if not nums:
            return ""
        return " " + "".join(f"[{n}]" for n in nums[:6])

    def _section_citations(self, section_name: str, evidence: list, source_idx: dict) -> list:
        by_source = source_idx.get("by_source", {})
        by_url = source_idx.get("by_url", {})
        section = section_name.lower()
        preferred_sources = []

        if section in {"competitive_landscape", "market_landscape", "strategic_implications"}:
            preferred_sources = ["serpapi", "newsapi", "gnews", "alpha_vantage_news", "github"]
        elif section in {"customer_and_user_signals", "go_to_market_implications"}:
            preferred_sources = ["reddit", "hackernews", "mastodon", "newsapi", "gnews"]
        elif section in {"product_implications", "feature_recommendations"}:
            preferred_sources = ["github", "github_trending", "newsapi", "serpapi"]
        elif section in {"risks_and_constraints", "decision_ready_next_steps"}:
            preferred_sources = ["newsapi", "serpapi", "alpha_vantage_news", "gnews"]
        else:
            preferred_sources = ["serpapi", "newsapi", "gnews", "github", "reddit"]

        nums = []
        for s in preferred_sources:
            n = by_source.get(s)
            if n:
                nums.append(n)

        for e in evidence[:16] if isinstance(evidence, list) else []:
            if not isinstance(e, dict):
                continue
            src = str(e.get("source", "")).strip().lower()
            url = str(e.get("url", "")).strip()
            if src in by_source:
                nums.append(by_source[src])
            if url in by_url:
                nums.append(by_url[url])

        return sorted({n for n in nums if isinstance(n, int) and n > 0})

    def _collect_bibliography(self, judged: JudgedDataset) -> list:
        seen = set()
        rows = []
        for item in judged.items:
            url = (item.url or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            rows.append({
                "source": (item.source or "unknown"),
                "title": (item.title or "(untitled)"),
                "url": url,
            })
        rows.sort(key=lambda r: (r["source"], r["title"]))
        return rows

    def _soft_wrap(self, text: str) -> str:
        t = str(text or "")
        t = re.sub(r"([/_\-])", r"\1<wbr/>", t)
        t = re.sub(r"([A-Za-z0-9]{35})(?=[A-Za-z0-9])", r"\1<wbr/>", t)
        return t

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#1f2937"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(16 * mm, 10 * mm, "Scout AI")
        canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def _safe_text(self, text: str, max_len: int = 12000) -> str:
        """
        Make arbitrary text safe for ReportLab Paragraph.
        Removes unicode junk that breaks Helvetica rendering.
        """
        t = "" if text is None else str(text)
        t = t[:max_len]

        # normalize unicode
        t = unicodedata.normalize("NFKC", t)

        char_map = {
            "\u2018": "'", "\u2019": "'",
            "\u201C": '"', "\u201D": '"',
            "\u2013": "-", "\u2014": "-", "\u2212": "-",
            "\u2026": "...",
            "\u00A0": " ",
        }

        t = t.translate(str.maketrans(char_map))

        # remove invisible unicode
        t = re.sub(r"[\u200B\u200C\u200D\uFEFF]", "", t)

        # remove problematic symbol blocks
        t = "".join(ch for ch in t if unicodedata.category(ch) not in {"So", "Cs"})

        # keep ascii only (safe for Helvetica)
        t = t.encode("ascii", "ignore").decode("ascii")

        # collapse whitespace
        t = re.sub(r"\s+", " ", t).strip()

        # escape XML chars
        t = html.escape(t, quote=False)

        # allow wrapping for long URLs without zero-width space
        t = re.sub(r"([/_\-])", r"\1<wbr/>", t)

        return t.replace("\n", "<br/>")

    def _p(self, text: str, style):
        return Paragraph(self._safe_text(text), style)

    def _link_p(self, url: str, style):
        u = (url or "").strip()
        safe_url = html.escape(u, quote=True)
        display = self._safe_text(u, max_len=500)
        return Paragraph(f'<link href="{safe_url}"><u>{display}</u></link>', style)

    def _bullets(self, items, style):
        return ListFlowable(
            [ListItem(self._p(str(i), style), leftIndent=6) for i in items if i],
            bulletType="bullet",
            bulletFontName="Helvetica",
            bulletFontSize=8,
            leftIndent=12,
        )

    def _section_title(self, label: str, style):
        return Paragraph(self._safe_text(f"{label}"), style)

    def render_pdf(self, query: str, judged: JudgedDataset, report: AnalysisReport, out_dir: str = "search_results") -> str:
        os.makedirs(out_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(out_dir, f"report_{ts}.pdf")

        doc = SimpleDocTemplate(
            file_path,
            pagesize=A4,
            leftMargin=14 * mm,
            rightMargin=14 * mm,
            topMargin=14 * mm,
            bottomMargin=16 * mm,
            title="Market Intelligence Report",
        )

        styles = getSampleStyleSheet()
        title = ParagraphStyle("TitleX", parent=styles["Title"], fontSize=22, leading=26, textColor=colors.HexColor("#111827"))
        h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, leading=17, textColor=colors.HexColor("#0f172a"), spaceBefore=8, spaceAfter=6)
        body = ParagraphStyle("BodyX", parent=styles["BodyText"], fontSize=10, leading=14, textColor=colors.HexColor("#111827"))
        small = ParagraphStyle("SmallX", parent=styles["BodyText"], fontSize=9, leading=12, textColor=colors.HexColor("#374151"))

        story = []
        logo_path = self._logo_path()
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=16 * mm, height=16 * mm)
            cover_head = Table(
                [[logo, Paragraph("Scout AI - Market Intelligence Report", title)]],
                colWidths=[20 * mm, 158 * mm],
            )
            cover_head.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.append(cover_head)
        else:
            story.append(Paragraph("Scout AI - Market Intelligence Report", title))
        story.append(Spacer(1, 6))
        story.append(self._p(f"Query: {query}", body))
        story.append(self._p(f"Generated: {datetime.utcnow().isoformat()}Z", small))
        story.append(self._p(f"Validated Items: {len(judged.items)} | Dropped: {judged.dropped_count}", small))
        story.append(Spacer(1, 8))

        summary_tbl = Table([[self._p("Executive Summary", h2)], [self._p(report.summary or "-", body)]], colWidths=[178 * mm])
        summary_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_tbl)
        story.append(Spacer(1, 10))

        sections = report.sections or {}
        evidence = sections.get("evidence_highlights", []) if isinstance(sections.get("evidence_highlights", []), list) else []

        story.append(self._section_title("Key Findings", h2))
        bibliography = self._collect_bibliography(judged)
        src_idx = self._source_index(bibliography)
        kf_cites = self._citation_text(self._section_citations("key_findings", evidence, src_idx))
        story.append(self._bullets(report.key_findings[:20], body))
        if kf_cites:
            story.append(self._p(f"Section Sources:{kf_cites}", small))

        story.append(self._section_title("Risks", h2))
        risk_cites = self._citation_text(self._section_citations("risks_and_constraints", evidence, src_idx))
        story.append(self._bullets(report.risks[:20], body))
        if risk_cites:
            story.append(self._p(f"Section Sources:{risk_cites}", small))

        story.append(self._section_title("Recommendations", h2))
        rec_cites = self._citation_text(self._section_citations("decision_ready_next_steps", evidence, src_idx))
        story.append(self._bullets(report.recommendations[:24], body))
        if rec_cites:
            story.append(self._p(f"Section Sources:{rec_cites}", small))

        for name in [
            "executive_overview", "business_context", "market_landscape",
            "customer_and_user_signals", "competitive_landscape", "product_implications",
            "feature_recommendations", "go_to_market_implications", "strategic_implications",
            "opportunities", "risks_and_constraints", "decision_ready_next_steps",
        ]:
            val = sections.get(name)
            if not val:
                continue
            story.append(PageBreak() if name in {"market_landscape", "feature_recommendations"} else Spacer(1, 4))
            story.append(self._section_title(name.replace("_", " ").title(), h2))
            section_cites = self._citation_text(self._section_citations(name, evidence, src_idx))
            if isinstance(val, list):
                story.append(self._bullets([str(v) for v in val[:40]], body))
            else:
                story.append(self._p(str(val), body))
            if section_cites:
                story.append(self._p(f"Section Sources:{section_cites}", small))

        evidence = sections.get("evidence_highlights", [])
        if isinstance(evidence, list) and evidence:
            story.append(PageBreak())
            story.append(self._section_title("Evidence Highlights", h2))
            rows = [["Title", "Source", "Why it matters"]]
            for e in evidence[:20]:
                rows.append([
                    self._p(str(e.get("title", ""))[:500], small),
                    self._p(str(e.get("source", "")), small),
                    self._p(str(e.get("why_it_matters", e.get("content", "")))[:700], small),
                ])

            t = Table(rows, colWidths=[78 * mm, 28 * mm, 72 * mm], repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(t)

        if bibliography:
            story.append(PageBreak())
            story.append(self._section_title("Sources (Bibliography)", h2))
            b_rows = [["#", "Source", "Title", "URL"]]
            for i, ref in enumerate(bibliography[:300], start=1):
                b_rows.append([
                    self._p(str(i), small),
                    self._p(ref["source"], small),
                    self._p(ref["title"][:320], small),
                    self._link_p(ref["url"][:500], small),
                ])
            b_table = Table(b_rows, colWidths=[10 * mm, 20 * mm, 66 * mm, 82 * mm], repeatRows=1)
            b_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            story.append(b_table)

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        return file_path