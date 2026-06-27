"""
PDF text extraction for AI Study Assistant.
"""

import fitz  # PyMuPDF


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF.

    Args:
        pdf_path: Path to the uploaded PDF.

    Returns:
        Extracted text as a single string.
    """

    text = ""

    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()

    return text.strip()