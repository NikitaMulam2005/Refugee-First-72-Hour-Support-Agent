# tools/pdf_generator.py
# FINAL VERSION – ALWAYS ENGLISH PDF (no matter user language) – NO ERRORS

import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


# ──────────────────────── Safe filename ────────────────────────
def _safe_filename(session_id: str) -> str:
    safe = re.sub(r"[^\w+-]", "_", session_id.strip()).replace("+", "plus")
    return f"wa_{safe or 'unknown'}.pdf"


# ──────────────────────── Generate PDF (ALWAYS ENGLISH) ────────────────────────
def generate_pdf(content: str, city: str, session_id: str) -> str:
    filename = _safe_filename(session_id)
    pdf_path = Path("downloads") / filename
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4,
                            leftMargin=60, rightMargin=60, topMargin=70, bottomMargin=60)

    # Get base styles and create custom ones WITHOUT 'parent' keyword
    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EngTitle",
        fontName=base_styles["Title"].fontName,  # Helvetica-Bold
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=30,
        leading=24
    )
    body_style = ParagraphStyle(
        "EngBody",
        fontName=base_styles["Normal"].fontName,  # Helvetica
        fontSize=11.5,
        leading=17,
        alignment=TA_JUSTIFY,
        spaceAfter=6
    )

    story = []

    # Title
    story.append(Paragraph(f"<b>Refugee First – Survival Plan for {city}</b>", title_style))
    story.append(Spacer(1, 20))

    # Clean markdown junk (stars, bold, bullets) – ensures clean English
    text = content
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)   # **bold**
    text = re.sub(r'\*(.*?)\*', r'\1', text)       # *italic* or bullets
    text = re.sub(r'__(.*?)__', r'\1', text)       # __bold__
    text = re.sub(r'_([^_]+)_', r'\1', text)       # _italic_
    text = re.sub(r'[*\-•►◆⭐★✦]', ' ', text)      # remove stray stars/bullets
    text = re.sub(r'\s+', ' ', text).strip()       # clean spaces

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 10))
            continue
        escaped = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        story.append(Paragraph(escaped, body_style))
        story.append(Spacer(1, 6))

    doc.build(story)
    return f"/downloads/{filename}"


# ──────────────────────── Test ────────────────────────
if __name__ == "__main__":
    test = """**Emergency Survival Guide for Mumbai**
* Airport → City Center: Local train (50 INR)
* Free shelter: Chhatrapati Shivaji Terminus
* Emergency: 100 or 112
Always in English, no matter what!"""
    print("English PDF generated →", generate_pdf(test, "Mumbai", "+919137398912"))