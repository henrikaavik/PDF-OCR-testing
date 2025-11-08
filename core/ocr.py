"""
OCR module using pytesseract with Estonian and English language support.
"""

import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from typing import List, Tuple
import io


def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Image.Image]:
    """
    Convert PDF bytes to list of PIL images.

    Args:
        pdf_bytes: PDF file as bytes
        dpi: DPI for image conversion (higher = better quality, slower)

    Returns:
        List of PIL Image objects, one per page
    """
    try:
        images = convert_from_bytes(pdf_bytes, dpi=dpi)
        return images
    except Exception as e:
        raise RuntimeError(f"PDF-i piltideks teisendamine ebaõnnestus: {str(e)}")


def ocr_image(image: Image.Image, languages: str = "est+eng") -> str:
    """
    Perform OCR on a single image.

    Args:
        image: PIL Image object
        languages: Tesseract language codes (e.g., "est+eng" for Estonian + English)

    Returns:
        Extracted text
    """
    try:
        # Configure tesseract
        custom_config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(
            image,
            lang=languages,
            config=custom_config
        )
        return text.strip()
    except Exception as e:
        raise RuntimeError(f"OCR ebaõnnestus: {str(e)}")


def ocr_pdf_page(pdf_bytes: bytes, page_num: int = 0, dpi: int = 300) -> str:
    """
    Perform OCR on a specific page of a PDF.

    Args:
        pdf_bytes: PDF file as bytes
        page_num: Page number (0-indexed)
        dpi: DPI for image conversion

    Returns:
        Extracted text from the page
    """
    images = pdf_to_images(pdf_bytes, dpi=dpi)

    if page_num >= len(images):
        raise ValueError(f"Lehekülg {page_num} ei eksisteeri (kokku {len(images)} lehte)")

    return ocr_image(images[page_num])


def ocr_pdf_all_pages(pdf_bytes: bytes, dpi: int = 300) -> List[Tuple[int, str]]:
    """
    Perform OCR on all pages of a PDF.

    Args:
        pdf_bytes: PDF file as bytes
        dpi: DPI for image conversion

    Returns:
        List of (page_number, extracted_text) tuples
    """
    images = pdf_to_images(pdf_bytes, dpi=dpi)
    results = []

    for i, image in enumerate(images):
        text = ocr_image(image)
        results.append((i, text))

    return results


def has_extractable_text(text: str, min_length: int = 50) -> bool:
    """
    Check if extracted text is substantial enough to be considered valid.

    Args:
        text: Extracted text
        min_length: Minimum length to consider text as extractable

    Returns:
        True if text is substantial, False otherwise
    """
    if not text:
        return False

    # Remove whitespace and check length
    clean_text = text.strip()
    return len(clean_text) >= min_length


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess image to improve OCR accuracy.
    Converts to grayscale and increases contrast.

    Args:
        image: PIL Image object

    Returns:
        Preprocessed PIL Image object
    """
    # Convert to grayscale
    image = image.convert('L')

    # Increase contrast (optional enhancement)
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    return image


def ocr_image_enhanced(image: Image.Image, languages: str = "est+eng") -> str:
    """
    Perform OCR with image preprocessing for better accuracy.

    Args:
        image: PIL Image object
        languages: Tesseract language codes

    Returns:
        Extracted text
    """
    preprocessed = preprocess_image_for_ocr(image)
    return ocr_image(preprocessed, languages)
