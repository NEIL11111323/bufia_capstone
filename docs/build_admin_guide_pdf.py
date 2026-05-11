from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "markdown" / "BUFIA_Admin_Guide_Polished.md"
OUTPUT = ROOT / "BUFIA_Admin_Guide_Polished.pdf"


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "GuideTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=10,
            alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "GuideH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0f5132"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "GuideH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#1d4ed8"),
            spaceBefore=8,
            spaceAfter=5,
        ),
        "h3": ParagraphStyle(
            "GuideH3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "GuideBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "meta": ParagraphStyle(
            "GuideMeta",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=12,
            textColor=colors.HexColor("#475569"),
            spaceAfter=3,
        ),
        "table": ParagraphStyle(
            "GuideTable",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1f2937"),
            backColor=colors.HexColor("#f8fafc"),
            borderPadding=5,
            borderWidth=0.5,
            borderColor=colors.HexColor("#cbd5e1"),
            spaceAfter=3,
        ),
    }


def flush_bullets(story, bullets, styles):
    if not bullets:
        return
    items = [
        ListItem(Paragraph(item, styles["body"]), leftIndent=8)
        for item in bullets
    ]
    story.append(
        ListFlowable(
            items,
            bulletType="bullet",
            bulletFontName="Helvetica",
            bulletFontSize=9,
            leftIndent=18,
            spaceAfter=6,
        )
    )
    bullets.clear()


def markdown_to_story(markdown_text):
    styles = build_styles()
    story = []
    bullets = []

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_bullets(story, bullets, styles)
            story.append(Spacer(1, 0.08 * inch))
            continue

        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
            continue

        flush_bullets(story, bullets, styles)

        if stripped.startswith("# "):
            story.append(Paragraph(stripped[2:].strip(), styles["title"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:].strip(), styles["h1"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(stripped[4:].strip(), styles["h2"]))
        elif stripped.startswith("#### "):
            story.append(Paragraph(stripped[5:].strip(), styles["h3"]))
        elif stripped.startswith("| ") or stripped == "| --- | --- | --- |":
            story.append(Paragraph(stripped.replace("|", "&#124;"), styles["table"]))
        elif stripped.startswith("Document name:") or stripped.startswith("Prepared from:") or stripped.startswith("Audience:") or stripped.startswith("System scope:"):
            story.append(Paragraph(stripped, styles["meta"]))
        else:
            story.append(Paragraph(stripped, styles["body"]))

    flush_bullets(story, bullets, styles)
    return story


def build_pdf():
    markdown_text = SOURCE.read_text(encoding="utf-8")
    story = markdown_to_story(markdown_text)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="BUFIA Admin Guide Polished",
        author="OpenAI Codex",
    )
    doc.build(story)


if __name__ == "__main__":
    build_pdf()
    print(OUTPUT)
