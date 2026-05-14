from __future__ import annotations

from io import BytesIO


def extract_text_from_pdf(file_bytes: bytes) -> str:
    # Prefer PyMuPDF for robustness; fallback to pdfplumber.
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text("text"))
        text = "\n".join(parts)
        if text.strip():
            return text
    except Exception:
        pass

    try:
        import pdfplumber

        parts = []
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)
    except Exception:
        return ""


def extract_text_from_docx(file_bytes: bytes) -> str:
    try:
        from docx import Document

        doc = Document(BytesIO(file_bytes))
        parts = [p.text for p in doc.paragraphs if p.text]
        return "\n".join(parts)
    except Exception:
        return ""

