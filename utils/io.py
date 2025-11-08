"""
XLSX export utilities with proper formatting.
Exports per-file summaries and quarterly aggregated reports.
"""

import io
from typing import List, Dict, Any
import pandas as pd
from utils.dates import get_month_name_estonian


# Fixed column order for exports
COLUMN_ORDER = ['Kuupäev', 'Töötaja', 'Projekt', 'Tunnid', 'Allikas']


def create_per_file_xlsx(
    data: List[Dict[str, Any]],
    filename: str,
    columns: List[str] = None,
    formatting: Dict[str, Any] = None
) -> bytes:
    """
    Create XLSX file for a single PDF's extracted data with optional visual formatting.

    Args:
        data: List of row dictionaries with schema fields + Allikas
        filename: Original PDF filename (used for Allikas column)
        columns: Optional list of column names. If None, uses standard COLUMN_ORDER
        formatting: Optional formatting metadata from Vision API with:
            - merged_cells: List of merged cell ranges
            - cell_borders: Dict mapping "row,col" to border info
            - header_rows: List of header row indices
            - total_rows: List of total row indices
            - bold_cells: List of [row, col] coordinates for bold cells

    Returns:
        XLSX file as bytes
    """
    # Determine column order
    if columns:
        # Use provided columns (from Vision API or custom extraction)
        column_order = columns + ['Allikas']
    else:
        # Use standard columns
        column_order = COLUMN_ORDER

    if not data:
        # Create empty DataFrame with correct columns
        df = pd.DataFrame(columns=column_order)
    else:
        # Add filename to each row
        for row in data:
            row['Allikas'] = filename

        df = pd.DataFrame(data)

        # Ensure all required columns exist
        for col in column_order:
            if col not in df.columns:
                df[col] = ''

        # Reorder columns
        df = df[[col for col in column_order if col in df.columns]]

    # Export to bytes
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Andmed')

        # Format the worksheet
        workbook = writer.book
        worksheet = writer.sheets['Andmed']

        # Initialize formatting dict if not provided
        if formatting is None:
            formatting = {}

        # Define default formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })

        bold_format = workbook.add_format({'bold': True})

        # Define border formats (for individual borders)
        border_formats = {}
        for top in [True, False]:
            for bottom in [True, False]:
                for left in [True, False]:
                    for right in [True, False]:
                        key = f"{top},{bottom},{left},{right}"
                        border_formats[key] = workbook.add_format({
                            'top': 1 if top else 0,
                            'bottom': 1 if bottom else 0,
                            'left': 1 if left else 0,
                            'right': 1 if right else 0
                        })

        # Apply merged cells if provided
        merged_cells = formatting.get('merged_cells', [])
        for merge in merged_cells:
            try:
                start_row = merge.get('start_row', 0) + 1  # +1 for header row
                start_col = merge.get('start_col', 0)
                end_row = merge.get('end_row', 0) + 1
                end_col = merge.get('end_col', 0)
                value = merge.get('value', '')

                # Validate range
                if end_row >= start_row and end_col >= start_col:
                    worksheet.merge_range(start_row, start_col, end_row, end_col, value, header_format)
            except Exception:
                # Skip invalid merge ranges
                pass

        # Format header row (default)
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Apply cell borders if provided
        cell_borders = formatting.get('cell_borders', {})
        for cell_key, borders in cell_borders.items():
            try:
                row_str, col_str = cell_key.split(',')
                row = int(row_str) + 1  # +1 for header row
                col = int(col_str)

                # Get cell value
                if row - 1 < len(df) and col < len(df.columns):
                    cell_value = df.iloc[row - 1, col]

                    # Create border format key
                    top = borders.get('top', False)
                    bottom = borders.get('bottom', False)
                    left = borders.get('left', False)
                    right = borders.get('right', False)
                    format_key = f"{top},{bottom},{left},{right}"

                    # Apply border
                    if format_key in border_formats:
                        worksheet.write(row, col, cell_value, border_formats[format_key])
            except Exception:
                # Skip invalid border specs
                pass

        # Apply bold cells if provided
        bold_cells = formatting.get('bold_cells', [])
        for cell_coord in bold_cells:
            try:
                if len(cell_coord) == 2:
                    row, col = cell_coord
                    row = row + 1  # +1 for header row

                    # Get cell value
                    if row - 1 < len(df) and col < len(df.columns):
                        cell_value = df.iloc[row - 1, col]
                        worksheet.write(row, col, cell_value, bold_format)
            except Exception:
                # Skip invalid cell coords
                pass

        # Auto-fit columns
        for i, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).apply(len).max(),
                len(col)
            ) + 2
            worksheet.set_column(i, i, min(max_len, 50))

    output.seek(0)
    return output.getvalue()


def create_quarterly_xlsx(
    raw_data: List[Dict[str, Any]],
    pivot_data: pd.DataFrame
) -> bytes:
    """
    Create quarterly XLSX report with two sheets:
    - Koond: Pivot summary (Töötaja × Projekt × month)
    - Toorandmed: All raw combined rows

    Args:
        raw_data: All combined raw rows from all files
        pivot_data: Pre-calculated pivot DataFrame

    Returns:
        XLSX file as bytes
    """
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })

        number_format = workbook.add_format({'num_format': '#,##0.00'})

        # Sheet 1: Koond (Pivot Summary)
        pivot_data.to_excel(writer, sheet_name='Koond')
        worksheet_koond = writer.sheets['Koond']

        # Format Koond sheet
        for col_num in range(len(pivot_data.columns) + 1):
            worksheet_koond.write(0, col_num,
                                 pivot_data.index.name if col_num == 0
                                 else pivot_data.columns[col_num - 1],
                                 header_format)

        # Sheet 2: Toorandmed (Raw Data)
        if raw_data:
            df_raw = pd.DataFrame(raw_data)

            # Ensure all required columns exist
            for col in COLUMN_ORDER:
                if col not in df_raw.columns:
                    df_raw[col] = ''

            # Reorder columns
            df_raw = df_raw[COLUMN_ORDER]
        else:
            df_raw = pd.DataFrame(columns=COLUMN_ORDER)

        df_raw.to_excel(writer, index=False, sheet_name='Toorandmed')
        worksheet_raw = writer.sheets['Toorandmed']

        # Format Toorandmed header
        for col_num, value in enumerate(df_raw.columns.values):
            worksheet_raw.write(0, col_num, value, header_format)

        # Format Tunnid column with number format
        if 'Tunnid' in df_raw.columns:
            tunnid_col_idx = df_raw.columns.get_loc('Tunnid')
            worksheet_raw.set_column(tunnid_col_idx, tunnid_col_idx, 12, number_format)

        # Auto-fit columns for both sheets
        for worksheet, df in [(worksheet_koond, pivot_data), (worksheet_raw, df_raw)]:
            for i, col in enumerate(df.columns):
                try:
                    max_len = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    ) + 2
                    worksheet.set_column(i + 1, i + 1, min(max_len, 50))
                except:
                    worksheet.set_column(i + 1, i + 1, 15)

    output.seek(0)
    return output.getvalue()


def create_validation_report_text(warnings: List[str]) -> str:
    """
    Create a text report of validation warnings.

    Args:
        warnings: List of warning messages

    Returns:
        Formatted text report
    """
    if not warnings:
        return "✓ Valideerimisvigu ei leitud"

    report = "⚠ Valideerimishoiatused:\n\n"
    for i, warning in enumerate(warnings, 1):
        report += f"{i}. {warning}\n"

    return report
