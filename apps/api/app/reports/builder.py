"""Renders a Product's assessment dossier to PDF bytes.

This module ASSEMBLES a document from data already stored on the Product/
Case/ComplianceItem/AbsAssessment rows - it never generates a new legal
claim, citation, or classification of its own. Every citation rendered in
the "IP/regulatory assessments" section comes from `Case.citations` (JSON
already written by app.chat.router at answer time); every citation in the
compliance/ABS sections comes from `ComplianceItem.evidence` /
`AbsAssessment.applicable_provisions` (already written by
app.compliance.service.attach_evidence / app.abs.service.attach_evidence
running the real retrieve/rerank pipeline). If a section has nothing to
show, this renders an honest "Not yet assessed" / "None recorded" line
rather than omitting the section - see CLAUDE.md: "Do not invent real
legal citations or government records."
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, TypedDict

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace

from app.db.models import AbsAssessment, ComplianceItem, Product

# CLAUDE.md caveat #4, reused verbatim (this is the one persistent
# disclaimer the project requires in header/footer strips) - never
# paraphrased, per that file's own instruction.
DISCLAIMER = "SIH 2026 Prototype - Not an official Government of India website"
LEGAL_NOTE = "Informational only - not legal advice."

_MAX_CASES_SHOWN = 5
_MAX_ANSWER_CHARS = 800

_PAGE_MARGIN = 15


class CaseEntry(TypedDict):
    """Plain-data view of one Case for the report - decouples the builder
    from both the ORM row and CaseOut (which doesn't carry citations)."""

    question: str
    answer: str
    confidence_level: str | None
    confidence_score: float | None
    status: str | None
    created_at: datetime | None
    citations: list[dict[str, Any]]


def _safe(text: Any) -> str:
    """fpdf2's built-in core fonts only support Latin-1. Never let a
    product/case field containing e.g. Devanagari text crash report
    generation - degrade unsupported characters instead of 500ing."""
    if text is None:
        return ""
    s = str(text)
    return s.encode("latin-1", "replace").decode("latin-1")


def _humanize(value: str | None) -> str:
    if not value:
        return "Not set"
    return value.replace("_", " ").replace("-", " ").title()


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


class _ReportPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-18)
        self.set_font("helvetica", "I", 7)
        self.set_text_color(110, 110, 110)
        self.multi_cell(
            0, 4, _safe(f"{DISCLAIMER}. {LEGAL_NOTE}"), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT
        )
        self.set_font("helvetica", "", 7)
        self.cell(0, 4, f"Page {self.page_no()}", align="C")


def _add_heading(pdf: _ReportPDF, text: str) -> None:
    pdf.ln(3)
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(0, 8, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(180, 180, 180)
    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + pdf.epw, pdf.get_y())
    pdf.ln(2)
    pdf.set_text_color(0, 0, 0)


def _add_subheading(pdf: _ReportPDF, text: str) -> None:
    pdf.set_font("helvetica", "B", 11)
    pdf.cell(0, 6, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _add_field(pdf: _ReportPDF, label: str, value: str) -> None:
    pdf.set_font("helvetica", "B", 10)
    pdf.write(5, _safe(f"{label}: "))
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 5, _safe(value or "Not set"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _add_body(pdf: _ReportPDF, text: str) -> None:
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 5, _safe(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _add_bullets(pdf: _ReportPDF, items: list[str]) -> None:
    pdf.set_font("helvetica", "", 10)
    for item in items:
        pdf.multi_cell(0, 5, _safe(f"- {item}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _format_evidence_line(ev: dict[str, Any]) -> str:
    """One evidence/citation row's display line - only fields actually
    present on the stored row are shown, nothing is looked up/invented."""
    doc_id = ev.get("doc_id") or "unknown-doc"
    title = ev.get("title")
    section = ev.get("section_or_article") or ev.get("section")
    authority = ev.get("authority")
    parts = [f"{doc_id}"]
    if title and title != doc_id:
        parts.append(f'"{title}"')
    if section:
        parts.append(f"sec. {section}")
    if authority:
        parts.append(f"({authority})")
    return " - ".join(parts)


def _add_product_overview(pdf: _ReportPDF, product: Product) -> None:
    _add_heading(pdf, "Product Overview")
    _add_field(pdf, "Description", product.description or "None recorded")
    _add_field(pdf, "Classification", _humanize(product.product_classification))
    _add_field(pdf, "Jurisdiction", _humanize(product.jurisdiction))
    _add_field(pdf, "Intended use", product.intended_use or "None recorded")
    _add_field(pdf, "Claims", product.claims or "None recorded")
    _add_field(pdf, "Development stage", _humanize(product.development_stage))
    _add_field(pdf, "Target market", product.target_market or "None recorded")

    pdf.ln(1)
    _add_subheading(pdf, "Ingredients")
    if product.ingredients:
        lines = []
        for ing in product.ingredients:
            name = ing.get("name", "Unnamed ingredient") if isinstance(ing, dict) else str(ing)
            qty = ing.get("quantity") if isinstance(ing, dict) else None
            lines.append(f"{name} ({qty})" if qty else name)
        _add_bullets(pdf, lines)
    else:
        _add_body(pdf, "None recorded")

    pdf.ln(1)
    _add_subheading(pdf, "Biological resources")
    if product.biological_resources:
        _add_bullets(pdf, [str(r) for r in product.biological_resources])
    else:
        _add_body(pdf, "None recorded")


def _add_cases_section(pdf: _ReportPDF, cases: list[CaseEntry]) -> None:
    _add_heading(pdf, "IP / Regulatory Assessments")
    if not cases:
        _add_body(pdf, "Not yet assessed - no questions have been asked about this product yet.")
        return

    shown = cases[:_MAX_CASES_SHOWN]
    overflow = len(cases) - len(shown)

    for i, case in enumerate(shown, start=1):
        pdf.ln(2)
        _add_subheading(pdf, f"Assessment {i} - {case['created_at'].strftime('%Y-%m-%d') if case['created_at'] else 'undated'}")
        _add_field(pdf, "Question", case["question"] or "")
        answer = (case["answer"] or "").strip()
        if answer:
            _add_field(pdf, "Answer", _truncate(answer, _MAX_ANSWER_CHARS))
        else:
            _add_field(pdf, "Answer", "Not yet answered")
        band = case.get("confidence_level")
        score = case.get("confidence_score")
        band_text = _humanize(band) if band else "Not available"
        if score is not None:
            band_text = f"{band_text} ({score:.2f})"
        _add_field(pdf, "Confidence", band_text)

        citations = case.get("citations") or []
        pdf.set_font("helvetica", "B", 10)
        pdf.cell(0, 5, "Citations:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if citations:
            _add_bullets(pdf, [_format_evidence_line(c) for c in citations])
        else:
            _add_body(pdf, "None recorded")

    if overflow > 0:
        pdf.ln(1)
        pdf.set_font("helvetica", "I", 9)
        pdf.multi_cell(
            0, 5,
            _safe(f"+{overflow} earlier assessment(s) not shown - see the app for the full history."),
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )


def _add_abs_section(pdf: _ReportPDF, abs_assessment: AbsAssessment | None) -> None:
    _add_heading(pdf, "Access and Benefit-Sharing (ABS) Status")
    if abs_assessment is None:
        _add_body(pdf, "Not yet assessed.")
        return

    _add_field(pdf, "Status", _humanize(abs_assessment.status.value))
    _add_field(pdf, "Preliminary framework", abs_assessment.preliminary_framework or "Not yet determined")

    pdf.ln(1)
    _add_subheading(pdf, "Next steps")
    if abs_assessment.next_steps:
        _add_bullets(pdf, [str(s) for s in abs_assessment.next_steps])
    else:
        _add_body(pdf, "None recorded")

    pdf.ln(1)
    _add_subheading(pdf, "Applicable provisions")
    if abs_assessment.applicable_provisions:
        _add_bullets(pdf, [_format_evidence_line(p) for p in abs_assessment.applicable_provisions])
    else:
        _add_body(pdf, "None recorded")


def _add_compliance_section(pdf: _ReportPDF, compliance: list[ComplianceItem]) -> None:
    _add_heading(pdf, "Compliance Checklist")
    if not compliance:
        _add_body(pdf, "Not yet assessed - no compliance checklist has been generated for this product.")
        return

    complete = sum(1 for item in compliance if item.status.value == "complete")
    _add_field(pdf, "Summary", f"{complete} of {len(compliance)} complete")
    pdf.ln(1)

    with pdf.table(
        col_widths=(24, 24, 21, 21),
        text_align="LEFT",
        line_height=5,
        headings_style=FontFace(emphasis="BOLD", size_pt=9),
    ) as table:
        header = table.row()
        for h in ("Area", "Status", "Reason", "Notes"):
            header.cell(h)
        for item in compliance:
            row = table.row()
            row.cell(_safe(_humanize(item.area.value)))
            row.cell(_safe(_humanize(item.status.value)))
            row.cell(_safe(item.applicability_reason or ""))
            row.cell(_safe(item.notes or "-"))


def build_product_report_pdf(
    product: Product,
    cases: list[CaseEntry],
    compliance: list[ComplianceItem],
    abs_assessment: AbsAssessment | None,
    generated_by: str,
    generated_at: datetime,
) -> bytes:
    """Assemble a Product's assessment dossier into a downloadable PDF.

    Pure assembly: every value rendered comes from `product`, `cases`,
    `compliance`, or `abs_assessment` as passed in - this function performs
    no DB/network I/O and invents nothing (see module docstring).
    """
    pdf = _ReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(_PAGE_MARGIN, _PAGE_MARGIN, _PAGE_MARGIN)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    # --- Header -------------------------------------------------------
    pdf.set_font("helvetica", "B", 18)
    pdf.multi_cell(0, 9, _safe(product.name or "Untitled product"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 5, _safe(f"{DISCLAIMER}. {LEGAL_NOTE}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)

    pdf.ln(2)
    pdf.set_font("helvetica", "", 9)
    pdf.cell(0, 5, _safe(f"Generated by: {generated_by}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 5, _safe(f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M UTC')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # --- Sections -------------------------------------------------------
    _add_product_overview(pdf, product)
    _add_cases_section(pdf, cases)
    _add_abs_section(pdf, abs_assessment)
    _add_compliance_section(pdf, compliance)

    output = pdf.output()
    return bytes(output)
