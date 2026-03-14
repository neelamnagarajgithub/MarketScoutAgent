import os
import re
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph, SimpleDocTemplate, Spacer, ListFlowable, ListItem, Table, TableStyle, PageBreak
)
import html

from app.pipeline.types import AnalysisReport, JudgedDataset


class ReportGenerator:
    def _soft_wrap(self, text: str) -> str:
        t = str(text or "")
        t = re.sub(r"([/_\-])", r"\1<wbr/>", t)
        t = re.sub(r"([A-Za-z0-9]{35})(?=[A-Za-z0-9])", r"\1<wbr/>", t)
        return t

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#1f2937"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(16 * mm, 10 * mm, "Market Intelligence Report")
        canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def _safe_text(self, text: str, max_len: int = 12000) -> str:
        """
        Make arbitrary text safe for ReportLab Paragraph (XML-like parser).
        """
        t = "" if text is None else str(text)
        t = t[:max_len]

        # Escape XML-sensitive chars first
        t = html.escape(t, quote=False)

        zws = "\u200b"  # zero-width space

        # Use lambda replacements to avoid "bad escape \\u" in re.sub replacement parsing
        t = re.sub(r"([/_\-.])", lambda m: f"{m.group(1)}{zws}", t)
        t = re.sub(r"([A-Za-z0-9]{32})(?=[A-Za-z0-9])", lambda m: f"{m.group(1)}{zws}", t)

        t = t.replace("\n", "<br/>")
        return t

    def _p(self, text: str, style):
        return Paragraph(self._safe_text(text), style)

    def _bullets(self, items, style):
        return ListFlowable(
            [ListItem(self._p(str(i), style), leftIndent=6) for i in items if i],
            bulletType="bullet",
            bulletFontName="Helvetica",
            bulletFontSize=8,
            leftIndent=12,
        )

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
        story.append(Paragraph("Market Intelligence Report", title))
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

        story.append(Paragraph("Key Findings", h2))
        story.append(self._bullets(report.key_findings[:20], body))
        story.append(Paragraph("Risks", h2))
        story.append(self._bullets(report.risks[:20], body))
        story.append(Paragraph("Recommendations", h2))
        story.append(self._bullets(report.recommendations[:24], body))

        sections = report.sections or {}
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
            story.append(Paragraph(name.replace("_", " ").title(), h2))
            if isinstance(val, list):
                story.append(self._bullets(val[:40], body))
            else:
                story.append(Paragraph(self._soft_wrap(str(val)), body))

        evidence = sections.get("evidence_highlights", [])
        if isinstance(evidence, list) and evidence:
            story.append(PageBreak())
            story.append(Paragraph("Evidence Highlights", h2))
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

        doc.build(story, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
        return file_path