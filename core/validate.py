"""
Rule-based validation module.
Validates extracted data against schema requirements and performs total consistency checks.
"""

from typing import List, Dict, Any, Tuple
from utils.dates import is_valid_date


TOTAL_TOLERANCE = 0.01


def validate_row(row: Dict[str, Any], row_num: int = 0) -> Tuple[bool, List[str]]:
    """
    Validate a single row against schema rules.

    Rules:
    - Kuupäev must be valid dd.mm.yyyy format in range 2000-2035
    - Tunnid must be numeric >= 0
    - Töötaja and Projekt must not be empty

    Args:
        row: Row dictionary
        row_num: Row number for error messages

    Returns:
        Tuple of (is_valid, list_of_warnings)
    """
    warnings = []
    is_valid = True

    # Validate Kuupäev
    if 'Kuupäev' not in row or row['Kuupäev'] is None:
        warnings.append(f"Rida {row_num}: Kuupäev puudub")
        is_valid = False
    elif not is_valid_date(str(row['Kuupäev'])):
        warnings.append(f"Rida {row_num}: Vigane kuupäev '{row['Kuupäev']}' (nõutav formaat: dd.mm.yyyy, aasta 2000-2035)")
        is_valid = False

    # Validate Tunnid
    if 'Tunnid' not in row or row['Tunnid'] is None:
        warnings.append(f"Rida {row_num}: Tunnid puudub")
        is_valid = False
    else:
        try:
            tunnid = float(row['Tunnid'])
            if tunnid < 0:
                warnings.append(f"Rida {row_num}: Tunnid ei saa olla negatiivne ({tunnid})")
                is_valid = False
        except (ValueError, TypeError):
            warnings.append(f"Rida {row_num}: Tunnid ei ole number '{row['Tunnid']}'")
            is_valid = False

    # Validate Töötaja
    if 'Töötaja' not in row or not row['Töötaja']:
        warnings.append(f"Rida {row_num}: Töötaja puudub")
        is_valid = False

    # Validate Projekt
    if 'Projekt' not in row or not row['Projekt']:
        warnings.append(f"Rida {row_num}: Projekt puudub")
        is_valid = False

    return (is_valid, warnings)


def validate_data(data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Validate all rows in extracted data.

    Args:
        data: List of row dictionaries

    Returns:
        Tuple of (valid_rows, all_warnings)
    """
    valid_rows = []
    all_warnings = []

    for i, row in enumerate(data, start=1):
        is_valid, warnings = validate_row(row, i)

        if is_valid:
            valid_rows.append(row)
        else:
            all_warnings.extend(warnings)

    return (valid_rows, all_warnings)


def calculate_total_hours(data: List[Dict[str, Any]]) -> float:
    """
    Calculate total hours from validated data.

    Args:
        data: List of row dictionaries

    Returns:
        Sum of all Tunnid values
    """
    total = 0.0

    for row in data:
        if 'Tunnid' in row and row['Tunnid'] is not None:
            try:
                total += float(row['Tunnid'])
            except (ValueError, TypeError):
                pass

    return round(total, 2)


def check_total_consistency(
    calculated_total: float,
    expected_total: float
) -> Tuple[bool, Optional[str]]:
    """
    Check if calculated total matches expected total within tolerance.

    Args:
        calculated_total: Sum of extracted hours
        expected_total: Expected total from document (e.g., from "Kokku" row)

    Returns:
        Tuple of (is_consistent, warning_message)
    """
    difference = abs(calculated_total - expected_total)

    if difference > TOTAL_TOLERANCE:
        warning = (
            f"Tundide summa ei klapi: arvutatud {calculated_total:.2f}, "
            f"dokumendis märgitud {expected_total:.2f} "
            f"(erinevus: {difference:.2f})"
        )
        return (False, warning)

    return (True, None)


def validate_file_data(
    data: List[Dict[str, Any]],
    expected_total: Optional[float] = None
) -> Dict[str, Any]:
    """
    Complete validation for a file's extracted data.

    Args:
        data: List of row dictionaries
        expected_total: Expected total hours from document (if found)

    Returns:
        Dictionary with:
        - valid_data: List of valid rows
        - warnings: List of all warning messages
        - total_hours: Calculated total
        - total_consistent: Whether totals match (if expected_total provided)
    """
    # Validate rows
    valid_data, warnings = validate_data(data)

    # Calculate total
    total_hours = calculate_total_hours(valid_data)

    # Check total consistency
    total_consistent = True
    if expected_total is not None:
        is_consistent, warning = check_total_consistency(total_hours, expected_total)
        total_consistent = is_consistent
        if not is_consistent and warning:
            warnings.append(warning)

    return {
        'valid_data': valid_data,
        'warnings': warnings,
        'total_hours': total_hours,
        'total_consistent': total_consistent,
        'valid_row_count': len(valid_data),
        'invalid_row_count': len(data) - len(valid_data)
    }
