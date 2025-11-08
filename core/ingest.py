"""
PDF ingestion and page classification module.
Validates page count and determines if pages need OCR or can use direct text extraction.
"""

import PyPDF2
import io
from typing import Tuple, List, Dict
from core.ocr import has_extractable_text


MAX_PAGES = 10


class PageLimitExceededError(Exception):
    """Raised when PDF has more than MAX_PAGES pages."""
    pass


def get_page_count(pdf_bytes: bytes) -> int:
    """
    Get the number of pages in a PDF.

    Args:
        pdf_bytes: PDF file as bytes

    Returns:
        Number of pages

    Raises:
        Exception: If PDF cannot be read
    """
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        return len(pdf_reader.pages)
    except Exception as e:
        raise RuntimeError(f"PDF-i lugemine ebaõnnestus: {str(e)}")


def validate_page_count(pdf_bytes: bytes, filename: str = "") -> int:
    """
    Validate that PDF has at most MAX_PAGES pages.

    Args:
        pdf_bytes: PDF file as bytes
        filename: Original filename for error message

    Returns:
        Number of pages if valid

    Raises:
        PageLimitExceededError: If PDF has more than MAX_PAGES pages
    """
    page_count = get_page_count(pdf_bytes)

    if page_count > MAX_PAGES:
        file_info = f" '{filename}'" if filename else ""
        raise PageLimitExceededError(
            f"Fail{file_info} sisaldab {page_count} lehekülge. "
            f"Maksimaalne lubatud arv on {MAX_PAGES} lehekülge. "
            f"Palun laadige üles lühem fail."
        )

    return page_count


def extract_text_from_page(pdf_bytes: bytes, page_num: int) -> str:
    """
    Extract text directly from a PDF page (without OCR).

    Args:
        pdf_bytes: PDF file as bytes
        page_num: Page number (0-indexed)

    Returns:
        Extracted text
    """
    try:
        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_file)

        if page_num >= len(pdf_reader.pages):
            return ""

        page = pdf_reader.pages[page_num]
        text = page.extract_text()
        return text.strip() if text else ""
    except Exception:
        return ""


def classify_page(pdf_bytes: bytes, page_num: int, min_text_length: int = 50) -> Tuple[str, str]:
    """
    Classify a page as 'text' (extractable) or 'ocr' (needs OCR).

    Args:
        pdf_bytes: PDF file as bytes
        page_num: Page number (0-indexed)
        min_text_length: Minimum text length to consider as extractable

    Returns:
        Tuple of (classification, extracted_text)
        classification: 'text' or 'ocr'
        extracted_text: Text extracted directly (empty if needs OCR)
    """
    text = extract_text_from_page(pdf_bytes, page_num)

    if has_extractable_text(text, min_text_length):
        return ('text', text)
    else:
        return ('ocr', '')


def classify_all_pages(pdf_bytes: bytes) -> List[Dict[str, any]]:
    """
    Classify all pages in a PDF.

    Args:
        pdf_bytes: PDF file as bytes

    Returns:
        List of page info dictionaries with keys:
        - page_num: Page number (0-indexed)
        - type: 'text' or 'ocr'
        - text: Extracted text (if type is 'text')
    """
    page_count = get_page_count(pdf_bytes)
    pages = []

    for i in range(page_count):
        page_type, text = classify_page(pdf_bytes, i)
        pages.append({
            'page_num': i,
            'type': page_type,
            'text': text
        })

    return pages


def ingest_pdf(pdf_bytes: bytes, filename: str = "") -> Dict[str, any]:
    """
    Ingest a PDF file: validate page count and classify pages.

    Args:
        pdf_bytes: PDF file as bytes
        filename: Original filename

    Returns:
        Dictionary with:
        - filename: Original filename
        - page_count: Number of pages
        - pages: List of page info dictionaries
        - valid: True if passed validation

    Raises:
        PageLimitExceededError: If PDF has too many pages
    """
    # Validate page count
    page_count = validate_page_count(pdf_bytes, filename)

    # Classify all pages
    pages = classify_all_pages(pdf_bytes)

    return {
        'filename': filename,
        'page_count': page_count,
        'pages': pages,
        'valid': True
    }
