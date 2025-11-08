"""
Schema normalization module.
Maps various header aliases to the 4 target columns and normalizes data.
"""

from typing import Dict, List, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import re


# Header mapping: aliases → target schema field
HEADER_MAPPING = {
    'Kuupäev': ['kuupäev', 'kuupaev', 'date', 'datum', 'kp', 'päev', 'paev'],
    'Töötaja': ['töötaja', 'tootaja', 'employee', 'name', 'nimi', 'worker', 'person', 'isik'],
    'Projekt': ['projekt', 'project', 'client', 'klient', 'customer', 'töö', 'too', 'task'],
    'Tunnid': ['tunnid', 'hours', 'h', 'tund', 'hrs', 'time', 'aeg', 'kestus']
}


def normalize_header_name(header: str) -> Optional[str]:
    """
    Normalize a header name to one of the target schema fields.

    Args:
        header: Original header name

    Returns:
        Target schema field name or None if no match
    """
    if not isinstance(header, str):
        return None

    # Clean and lowercase
    clean_header = header.strip().lower()

    # Check each target field's aliases
    for target, aliases in HEADER_MAPPING.items():
        if clean_header in [alias.lower() for alias in aliases]:
            return target

    return None


def map_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Map DataFrame columns to target schema using header aliases.

    Args:
        df: Input DataFrame

    Returns:
        DataFrame with normalized column names
    """
    new_columns = {}

    for col in df.columns:
        normalized = normalize_header_name(col)
        if normalized:
            new_columns[col] = normalized

    # Rename columns
    df = df.rename(columns=new_columns)

    return df


def normalize_tunnid(value: Any) -> Optional[Decimal]:
    """
    Normalize hours value to Decimal with 2 decimal places (half-up rounding).
    Accepts both comma and dot as decimal separator.

    Args:
        value: Input value (string, number, etc.)

    Returns:
        Decimal value rounded to 2 places, or None if invalid
    """
    if pd.isna(value) or value == '':
        return None

    try:
        # Convert to string first
        str_value = str(value).strip()

        # Replace comma with dot
        str_value = str_value.replace(',', '.')

        # Remove any whitespace
        str_value = str_value.replace(' ', '')

        # Parse to Decimal
        decimal_value = Decimal(str_value)

        # Check if non-negative
        if decimal_value < 0:
            return None

        # Round to 2 decimal places (half-up)
        rounded = decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        return rounded

    except Exception:
        return None


def normalize_date(value: Any) -> Optional[str]:
    """
    Normalize date value to dd.mm.yyyy format string.

    Args:
        value: Input date value

    Returns:
        Date string in dd.mm.yyyy format, or None if invalid
    """
    if pd.isna(value) or value == '':
        return None

    # Already a string, just clean it
    if isinstance(value, str):
        return value.strip()

    # Try to convert to string
    try:
        return str(value).strip()
    except:
        return None


def normalize_text_field(value: Any) -> Optional[str]:
    """
    Normalize text field (Töötaja, Projekt).

    Args:
        value: Input text value

    Returns:
        Cleaned string, or None if empty
    """
    if pd.isna(value) or value == '':
        return None

    try:
        text = str(value).strip()
        return text if text else None
    except:
        return None


def normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single data row to match schema.

    Args:
        row: Input row dictionary

    Returns:
        Normalized row dictionary with schema fields
    """
    normalized = {}

    # Normalize each field
    if 'Kuupäev' in row:
        normalized['Kuupäev'] = normalize_date(row['Kuupäev'])

    if 'Töötaja' in row:
        normalized['Töötaja'] = normalize_text_field(row['Töötaja'])

    if 'Projekt' in row:
        normalized['Projekt'] = normalize_text_field(row['Projekt'])

    if 'Tunnid' in row:
        tunnid = normalize_tunnid(row['Tunnid'])
        # Convert Decimal to float for JSON/DataFrame compatibility
        normalized['Tunnid'] = float(tunnid) if tunnid is not None else None

    return normalized


def normalize_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Normalize entire DataFrame to schema.

    Args:
        df: Input DataFrame (with potentially mapped column names)

    Returns:
        List of normalized row dictionaries
    """
    # First map column names
    df = map_dataframe_columns(df)

    # Filter to only schema columns
    schema_cols = ['Kuupäev', 'Töötaja', 'Projekt', 'Tunnid']
    available_cols = [col for col in schema_cols if col in df.columns]

    if not available_cols:
        return []

    # Get subset
    df_subset = df[available_cols]

    # Normalize each row
    normalized_rows = []

    for _, row in df_subset.iterrows():
        row_dict = row.to_dict()
        normalized = normalize_row(row_dict)

        # Only include rows with at least one non-null value
        if any(v is not None for v in normalized.values()):
            normalized_rows.append(normalized)

    return normalized_rows


def find_total_row(df: pd.DataFrame) -> Optional[float]:
    """
    Find "total" row in DataFrame (marked with "Kokku" or "Total").
    Returns the total hours value if found.

    Args:
        df: DataFrame

    Returns:
        Total hours value, or None if not found
    """
    # Look for rows containing "kokku" or "total"
    total_keywords = ['kokku', 'total', 'summa', 'sum', 'yhteensä', 'yhteensa']

    for _, row in df.iterrows():
        # Check all cells in the row
        for cell in row:
            if isinstance(cell, str):
                cell_lower = cell.strip().lower()
                if any(keyword in cell_lower for keyword in total_keywords):
                    # Found a total row, try to extract hours
                    for value in row:
                        normalized = normalize_tunnid(value)
                        if normalized is not None and normalized > 0:
                            return float(normalized)

    return None
