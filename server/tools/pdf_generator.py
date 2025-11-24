# tools/pdf_generator.py  ← change only this part

import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(content: str, city: str, session_id: str):
    """Simple fallback PDF – works on Windows with zero setup"""
    pdf_path = f"downloads/{session_id}.pdf"
    os.makedirs("downloads", exist_ok=True)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph(f"<b>Refugee First – Survival Plan for {city}</b>", styles['Title']))
    story.append(Spacer(1, 20))
    
    # Split content by lines and add as paragraphs
    for line in content.split('\n'):
        if line.strip():
            story.append(Paragraph(line.replace('\n', '<br/>'), styles['Normal']))
            story.append(Spacer(1, 12))
    
    doc.build(story)
    return pdf_path