"""Render saved fictional patent workspaces as explicitly unverified reports."""

import io
import re
from typing import Any
from xml.sax.saxutils import escape

TITLE = "SmartProBono Counsel | Patent Review Draft"
NOTICE = (
    "FICTIONAL DATA ONLY - UNVERIFIED REVIEW DRAFT. No patentability opinion, "
    "verified evidence, deadline calculation, approved response or filing."
)
MAX_CHARS = 180_000

_DISCLOSURE_LABELS = (
    ("title", "Working invention title"),
    ("problem", "Technical problem"),
    ("solution", "Technical solution"),
    ("alternatives", "Alternative embodiments"),
    ("disclosures", "Reported public disclosures and dates"),
    ("contributions", "Potential contributors"),
    ("officeAction", "Manual Office Action notes"),
)
_CLAIM_LABELS = (
    ("element", "Claim element"),
    ("disclosureSupport", "Reported disclosure support"),
    ("reference", "Candidate prior art reference"),
    ("referencePassage", "Reported pinpoint passage"),
    ("status", "Reviewer mapping status"),
    ("notes", "Open issues"),
)


def _safe_text(value: Any) -> str:
    # XML 1.0 control characters cannot occur in a DOCX document. Mark rather
    # than silently dropping unsupported characters.
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]", "\ufffd", str(value or ""))


def report_sections(data: dict[str, Any]) -> list[tuple[str, str]]:
    """One ordered representation for both renderers; never trust verified flags."""
    disclosure = data.get("disclosure") or {}
    fields = disclosure.get("fields") or {}
    sections = [
        ("Workspace", _safe_text(data.get("title"))),
        ("Disclosure version", str(disclosure.get("version") or "Not saved")),
        ("Disclosure SHA-256", _safe_text(disclosure.get("content_sha256")) or "Not saved"),
    ]
    sections.extend((label, _safe_text(fields.get(key))) for key, label in _DISCLOSURE_LABELS)
    for index, row in enumerate(data.get("elements") or [], start=1):
        sections.append((f"Claim mapping {index}", "Unverified candidate; check sources independently."))
        sections.extend((label, _safe_text(row.get(key))) for key, label in _CLAIM_LABELS)
    sections.append(("Practitioner notes", _safe_text(data.get("reviewer_notes"))))
    sections.append(
        (
            "Review gates",
            "Confirm all facts, claim language, cited passages, applicable dates and current law. "
            "Separate prior-art and Office Action workbench exports are not included.",
        )
    )
    if sum(len(label) + len(value) for label, value in sections) > MAX_CHARS:
        raise ValueError("Report exceeds the preview size limit")
    return sections


def render_docx(data: dict[str, Any]) -> bytes:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor

    sections = report_sections(data)
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.75)
    section.bottom_margin = Inches(0.75)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    header = section.header.paragraphs[0]
    header.add_run("SMARTPROBONO COUNSEL | FICTIONAL DRAFT").bold = True
    footer = section.footer.paragraphs[0]
    footer.add_run("UNVERIFIED | Practitioner review required").italic = True
    heading = doc.add_heading(TITLE, level=0)
    for run in heading.runs:
        run.font.color.rgb = RGBColor.from_string("10263D")
    doc.add_paragraph(NOTICE)
    for label, value in sections:
        doc.add_heading(label, level=2)
        doc.add_paragraph(value or "Not recorded")
    doc.add_paragraph(NOTICE)
    stream = io.BytesIO()
    doc.save(stream)
    return stream.getvalue()


def render_pdf(data: dict[str, Any]) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    sections = report_sections(data)
    # The built-in PDF font uses WinAnsi. Refuse unsupported glyphs rather than
    # replace them silently. DOCX remains available for other scripts.
    for label, value in sections:
        try:
            (label + value).encode("cp1252")
        except UnicodeEncodeError as exc:
            raise ValueError("PDF preview cannot represent this text; export Word instead") from exc
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CounselTitle", parent=styles["Title"], textColor=colors.HexColor("#10263D")
    )
    heading_style = ParagraphStyle(
        "CounselHeading", parent=styles["Heading2"], textColor=colors.HexColor("#0D766E")
    )
    body = styles["BodyText"]

    def paragraph(value: str, style: Any) -> Any:
        return Paragraph(escape(value).replace("\n", "<br/>"), style)

    story = [paragraph(TITLE, title_style), paragraph(NOTICE, body), Spacer(1, 12)]
    for label, value in sections:
        story.append(paragraph(label, heading_style))
        story.append(paragraph(value or "Not recorded", body))
    story.extend([Spacer(1, 12), paragraph(NOTICE, body)])

    def page_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#10263D"))
        canvas.drawString(54, 30, "FICTIONAL DRAFT | UNVERIFIED")
        canvas.drawRightString(558, 30, f"Page {document.page}")
        canvas.restoreState()

    stream = io.BytesIO()
    doc = SimpleDocTemplate(
        stream, pagesize=letter, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=54
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return stream.getvalue()
