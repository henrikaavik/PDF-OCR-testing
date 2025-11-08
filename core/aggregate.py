"""
Quarterly aggregation module.
Creates pivot summaries and aggregates data across multiple files.
"""

from typing import List, Dict, Any, Tuple
import pandas as pd
from utils.dates import get_quarter, get_month, get_month_name_estonian, get_year, format_quarter


def add_derived_fields(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add derived fields (year, quarter, month) to each row.

    Args:
        data: List of validated row dictionaries

    Returns:
        List of rows with added fields
    """
    enriched = []

    for row in data:
        if 'Kuupäev' not in row or row['Kuupäev'] is None:
            continue

        row_copy = row.copy()

        # Add derived fields
        row_copy['Kvartal'] = get_quarter(row['Kuupäev'])
        row_copy['Kuu'] = get_month(row['Kuupäev'])
        row_copy['Aasta'] = get_year(row['Kuupäev'])

        enriched.append(row_copy)

    return enriched


def get_quarters_from_data(data: List[Dict[str, Any]]) -> List[Tuple[int, int]]:
    """
    Get unique (year, quarter) tuples from data.

    Args:
        data: List of row dictionaries with derived fields

    Returns:
        Sorted list of (year, quarter) tuples
    """
    quarters = set()

    for row in data:
        if 'Aasta' in row and 'Kvartal' in row:
            if row['Aasta'] is not None and row['Kvartal'] is not None:
                quarters.add((row['Aasta'], row['Kvartal']))

    return sorted(list(quarters))


def create_pivot_summary(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create pivot summary: Töötaja × Projekt × Month with sum(Tunnid).

    Args:
        data: List of row dictionaries with derived fields

    Returns:
        Pivot DataFrame
    """
    if not data:
        return pd.DataFrame()

    # Convert to DataFrame
    df = pd.DataFrame(data)

    # Ensure required columns exist
    required_cols = ['Töötaja', 'Projekt', 'Kuu', 'Tunnid']
    for col in required_cols:
        if col not in df.columns:
            return pd.DataFrame()

    # Add month name for display
    df['Kuu_nimi'] = df['Kuu'].apply(lambda m: get_month_name_estonian(m) if m else '')

    # Create pivot table
    try:
        pivot = pd.pivot_table(
            df,
            values='Tunnid',
            index=['Töötaja', 'Projekt'],
            columns='Kuu_nimi',
            aggfunc='sum',
            fill_value=0,
            margins=True,
            margins_name='Kokku'
        )

        # Round to 2 decimals
        pivot = pivot.round(2)

        return pivot

    except Exception as e:
        # If pivot fails, create a simple summary
        summary = df.groupby(['Töötaja', 'Projekt'])['Tunnid'].sum().reset_index()
        summary['Tunnid'] = summary['Tunnid'].round(2)
        return summary


def aggregate_multiple_files(
    file_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Aggregate data from multiple files into a quarterly report.

    Args:
        file_results: List of file processing results, each with 'valid_data' key

    Returns:
        Dictionary with:
        - all_data: Combined raw data from all files
        - enriched_data: Data with derived fields (quarter, month)
        - pivot: Pivot summary DataFrame
        - quarters: List of (year, quarter) tuples
        - total_hours: Total hours across all files
        - total_rows: Total valid rows
    """
    # Combine all valid data
    all_data = []

    for result in file_results:
        if 'valid_data' in result and result['valid_data']:
            all_data.extend(result['valid_data'])

    if not all_data:
        return {
            'all_data': [],
            'enriched_data': [],
            'pivot': pd.DataFrame(),
            'quarters': [],
            'total_hours': 0.0,
            'total_rows': 0
        }

    # Add derived fields
    enriched_data = add_derived_fields(all_data)

    # Get quarters
    quarters = get_quarters_from_data(enriched_data)

    # Create pivot
    pivot = create_pivot_summary(enriched_data)

    # Calculate totals
    total_hours = sum(row.get('Tunnid', 0) for row in all_data)
    total_rows = len(all_data)

    return {
        'all_data': all_data,
        'enriched_data': enriched_data,
        'pivot': pivot,
        'quarters': quarters,
        'total_hours': round(total_hours, 2),
        'total_rows': total_rows
    }


def get_quarter_summary_text(
    quarters: List[Tuple[int, int]],
    total_hours: float,
    total_rows: int
) -> str:
    """
    Generate a text summary of quarterly aggregation.

    Args:
        quarters: List of (year, quarter) tuples
        total_hours: Total hours
        total_rows: Total rows

    Returns:
        Formatted summary text
    """
    if not quarters:
        return "Kvartaleid ei leitud"

    quarter_strs = [format_quarter(year, q) for year, q in quarters]

    if len(quarters) == 1:
        summary = f"Kvartal: {quarter_strs[0]}\n"
    else:
        summary = f"Kvartalid: {', '.join(quarter_strs)}\n"

    summary += f"Kokku ridu: {total_rows}\n"
    summary += f"Kokku tunde: {total_hours:.2f}"

    return summary
