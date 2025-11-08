"""
Date parsing and quarter calculation utilities.
Strict dd.mm.yyyy format validation with year range 2000-2035.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


DATE_PATTERN = re.compile(r'^(\d{2})\.(\d{2})\.(\d{4})$')
MIN_YEAR = 2000
MAX_YEAR = 2035


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date in strict dd.mm.yyyy format.

    Args:
        date_str: Date string to parse

    Returns:
        datetime object if valid, None otherwise
    """
    if not isinstance(date_str, str):
        return None

    date_str = date_str.strip()
    match = DATE_PATTERN.match(date_str)

    if not match:
        return None

    day, month, year = match.groups()

    try:
        dt = datetime.strptime(f"{day}.{month}.{year}", "%d.%m.%Y")

        # Validate year range
        if not (MIN_YEAR <= dt.year <= MAX_YEAR):
            return None

        return dt
    except ValueError:
        return None


def is_valid_date(date_str: str) -> bool:
    """
    Check if date string is valid.

    Args:
        date_str: Date string to validate

    Returns:
        True if valid, False otherwise
    """
    return parse_date(date_str) is not None


def get_quarter(date_str: str) -> Optional[int]:
    """
    Get quarter (1-4) from date string.

    Args:
        date_str: Date string in dd.mm.yyyy format

    Returns:
        Quarter number (1-4) or None if invalid date
    """
    dt = parse_date(date_str)
    if dt is None:
        return None

    return (dt.month - 1) // 3 + 1


def get_month(date_str: str) -> Optional[int]:
    """
    Get month (1-12) from date string.

    Args:
        date_str: Date string in dd.mm.yyyy format

    Returns:
        Month number (1-12) or None if invalid date
    """
    dt = parse_date(date_str)
    if dt is None:
        return None

    return dt.month


def get_year(date_str: str) -> Optional[int]:
    """
    Get year from date string.

    Args:
        date_str: Date string in dd.mm.yyyy format

    Returns:
        Year or None if invalid date
    """
    dt = parse_date(date_str)
    if dt is None:
        return None

    return dt.year


def get_year_quarter(date_str: str) -> Optional[Tuple[int, int]]:
    """
    Get year and quarter from date string.

    Args:
        date_str: Date string in dd.mm.yyyy format

    Returns:
        Tuple of (year, quarter) or None if invalid date
    """
    dt = parse_date(date_str)
    if dt is None:
        return None

    quarter = (dt.month - 1) // 3 + 1
    return (dt.year, quarter)


def format_quarter(year: int, quarter: int) -> str:
    """
    Format year and quarter as string.

    Args:
        year: Year
        quarter: Quarter (1-4)

    Returns:
        Formatted string like "2024 Q1"
    """
    return f"{year} Q{quarter}"


def get_month_name_estonian(month: int) -> str:
    """
    Get Estonian month name.

    Args:
        month: Month number (1-12)

    Returns:
        Estonian month name
    """
    months = {
        1: "Jaanuar",
        2: "Veebruar",
        3: "Märts",
        4: "Aprill",
        5: "Mai",
        6: "Juuni",
        7: "Juuli",
        8: "August",
        9: "September",
        10: "Oktoober",
        11: "November",
        12: "Detsember"
    }
    return months.get(month, str(month))
