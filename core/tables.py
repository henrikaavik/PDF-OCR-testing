"""
Table extraction module using pdfplumber, camelot, and fallback heuristics.
Extracts multiple tables from each page and merges them.
"""

import io
import re
from typing import List, Dict, Any, Optional
import pandas as pd
import pdfplumber
try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False


def extract_tables_pdfplumber(pdf_bytes: bytes, page_num: Optional[int] = None) -> List[pd.DataFrame]:
    """
    Extract tables using pdfplumber.

    Args:
        pdf_bytes: PDF file as bytes
        page_num: Specific page number (0-indexed), or None for all pages

    Returns:
        List of DataFrames, one per detected table
    """
    tables = []

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            pages = [pdf.pages[page_num]] if page_num is not None else pdf.pages

            for page in pages:
                page_tables = page.extract_tables()

                for table in page_tables:
                    if table and len(table) > 0:
                        # Convert to DataFrame
                        df = pd.DataFrame(table[1:], columns=table[0])
                        tables.append(df)

    except Exception as e:
        # pdfplumber failed, return empty list
        pass

    return tables


def extract_tables_camelot(pdf_bytes: bytes, page_num: Optional[int] = None, flavor: str = 'lattice') -> List[pd.DataFrame]:
    """
    Extract tables using camelot.

    Args:
        pdf_bytes: PDF file as bytes
        page_num: Specific page number (1-indexed for camelot!), or None for all pages
        flavor: 'lattice' or 'stream'

    Returns:
        List of DataFrames, one per detected table
    """
    if not CAMELOT_AVAILABLE:
        return []

    tables = []

    try:
        # Save to temporary file (camelot requires file path)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        # Extract tables
        pages = str(page_num + 1) if page_num is not None else 'all'
        camelot_tables = camelot.read_pdf(tmp_path, pages=pages, flavor=flavor)

        for table in camelot_tables:
            df = table.df
            if not df.empty:
                tables.append(df)

        # Clean up temp file
        import os
        os.unlink(tmp_path)

    except Exception as e:
        # camelot failed, return empty list
        pass

    return tables


def parse_table_from_text(text: str) -> Optional[pd.DataFrame]:
    """
    Fallback heuristic: try to parse table structure from OCR text.
    Looks for tabular patterns with multiple rows and columns.

    Args:
        text: OCR extracted text

    Returns:
        DataFrame if table structure detected, None otherwise
    """
    lines = text.split('\n')
    lines = [line.strip() for line in lines if line.strip()]

    if len(lines) < 2:
        return None

    # Try to detect consistent column separators (tabs, multiple spaces, |)
    rows = []

    for line in lines:
        # Split by multiple spaces, tabs, or pipes
        parts = re.split(r'\s{2,}|\t+|\|', line)
        parts = [p.strip() for p in parts if p.strip()]

        if len(parts) >= 2:  # At least 2 columns
            rows.append(parts)

    if len(rows) < 2:
        return None

    # Check if rows have similar column counts
    col_counts = [len(row) for row in rows]
    most_common_count = max(set(col_counts), key=col_counts.count)

    # Filter rows with the most common column count
    filtered_rows = [row for row in rows if len(row) == most_common_count]

    if len(filtered_rows) < 2:
        return None

    # First row is likely header
    df = pd.DataFrame(filtered_rows[1:], columns=filtered_rows[0])
    return df


def extract_tables_from_page(
    pdf_bytes: bytes,
    page_num: int,
    page_text: Optional[str] = None
) -> List[pd.DataFrame]:
    """
    Extract all tables from a single page using multiple methods.
    Tries pdfplumber → camelot (lattice) → camelot (stream) → text heuristics.

    Args:
        pdf_bytes: PDF file as bytes
        page_num: Page number (0-indexed)
        page_text: Pre-extracted text from page (for fallback)

    Returns:
        List of DataFrames (may be empty if no tables found)
    """
    tables = []

    # Method 1: pdfplumber
    tables = extract_tables_pdfplumber(pdf_bytes, page_num)
    if tables:
        return tables

    # Method 2: camelot lattice
    tables = extract_tables_camelot(pdf_bytes, page_num, flavor='lattice')
    if tables:
        return tables

    # Method 3: camelot stream
    tables = extract_tables_camelot(pdf_bytes, page_num, flavor='stream')
    if tables:
        return tables

    # Method 4: text-based fallback
    if page_text:
        table = parse_table_from_text(page_text)
        if table is not None:
            tables = [table]

    return tables


def merge_tables(tables: List[pd.DataFrame]) -> pd.DataFrame:
    """
    Merge multiple tables from the same file.
    Attempts to align columns by header names.

    Args:
        tables: List of DataFrames to merge

    Returns:
        Single merged DataFrame
    """
    if not tables:
        return pd.DataFrame()

    if len(tables) == 1:
        return tables[0]

    # Try to concatenate with same columns
    # First, normalize column names across tables
    normalized_tables = []

    for table in tables:
        # Clean column names
        table.columns = [str(col).strip() for col in table.columns]
        normalized_tables.append(table)

    # Concatenate all tables
    try:
        merged = pd.concat(normalized_tables, ignore_index=True, sort=False)
        return merged
    except Exception:
        # If concat fails, just return the first table
        return normalized_tables[0]


def extract_all_tables(pdf_bytes: bytes, pages_info: List[Dict[str, Any]]) -> List[pd.DataFrame]:
    """
    Extract all tables from all pages in a PDF.

    Args:
        pdf_bytes: PDF file as bytes
        pages_info: List of page info dicts from ingest.classify_all_pages()

    Returns:
        List of all extracted DataFrames across all pages
    """
    all_tables = []

    for page_info in pages_info:
        page_num = page_info['page_num']
        page_text = page_info.get('text', '')

        page_tables = extract_tables_from_page(pdf_bytes, page_num, page_text)
        all_tables.extend(page_tables)

    return all_tables
