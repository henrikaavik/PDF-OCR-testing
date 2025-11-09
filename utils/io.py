"""
XLSX export utilities with proper formatting.
Exports per-file summaries with Vision API formatting preservation.
"""

import io
from typing import List, Dict, Any
import pandas as pd


def create_per_file_xlsx(
    data: List[Dict[str, Any]],
    filename: str,
    columns: List[str] = None,
    formatting: Dict[str, Any] = None,
    tables: List[Dict[str, Any]] = None
) -> bytes:
    """
    Create XLSX file for a single PDF's extracted data with optional visual formatting.

    Args:
        data: List of row dictionaries (LEGACY: flattened from all tables)
        filename: Original PDF filename (for reference)
        columns: Optional list of column names from Vision API (LEGACY)
        formatting: Optional formatting metadata from Vision API (LEGACY)
        tables: NEW - List of separate table objects with:
            - section_title: Optional section header text
            - columns: List of column names for this table
            - rows: List of row dicts for this table
            - formatting: Formatting metadata for this table

    Returns:
        XLSX file as bytes
    """
    # Export to bytes
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('Andmed')

        # Use NEW tables format if provided, otherwise fall back to legacy
        if tables and len(tables) > 0:
            # NEW FORMAT: Write multiple tables vertically with spacing
            current_row = 0

            for table_idx, table in enumerate(tables):
                section_title = table.get('section_title')
                table_columns = table.get('columns', [])
                table_rows = table.get('rows', [])
                table_formatting = table.get('formatting', {})

                # Write section title if present (in blue header style)
                if section_title:
                    section_format = workbook.add_format({
                        'bold': True,
                        'bg_color': '#4F81BD',  # Blue
                        'font_color': 'white',
                        'border': 1
                    })
                    # Merge cells for section title
                    if len(table_columns) > 1:
                        worksheet.merge_range(current_row, 0, current_row, len(table_columns) - 1, section_title, section_format)
                    else:
                        worksheet.write(current_row, 0, section_title, section_format)
                    current_row += 1

                # Create DataFrame for this table
                if table_rows:
                    df = pd.DataFrame(table_rows)
                    # Reorder columns
                    if table_columns:
                        for col in table_columns:
                            if col not in df.columns:
                                df[col] = ''
                        df = df[[col for col in table_columns if col in df.columns]]
                else:
                    df = pd.DataFrame(columns=table_columns)

                # Write table with formatting
                header_row = current_row
                _write_table_with_formatting(
                    worksheet, workbook, df, table_formatting,
                    start_row=current_row
                )

                # Move to next table position (add spacing)
                current_row += len(df) + 1  # +1 for header
                current_row += 2  # Add 2 empty rows between tables

        else:
            # LEGACY FORMAT: Single flattened table
            if not data:
                df = pd.DataFrame(columns=columns if columns else [])
            else:
                df = pd.DataFrame(data)
                if columns and set(columns) != set(df.columns):
                    for col in columns:
                        if col not in df.columns:
                            df[col] = ''
                    df = df[[col for col in columns if col in df.columns]]

            _write_table_with_formatting(
                worksheet, workbook, df, formatting if formatting else {},
                start_row=0
            )

    output.seek(0)
    return output.getvalue()


def _write_table_with_formatting(
    worksheet, workbook, df: pd.DataFrame, formatting: Dict[str, Any],
    start_row: int = 0
):
    """
    Helper function to write a single table with formatting.

    Args:
        worksheet: xlsxwriter worksheet
        workbook: xlsxwriter workbook
        df: DataFrame to write
        formatting: Formatting metadata
        start_row: Starting row position
    """

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
            merge_start_row = merge.get('start_row', 0) + start_row + 1  # +start_row for table position, +1 for header
            merge_start_col = merge.get('start_col', 0)
            merge_end_row = merge.get('end_row', 0) + start_row + 1
            merge_end_col = merge.get('end_col', 0)
            value = merge.get('value', '')

            # Validate range
            if merge_end_row >= merge_start_row and merge_end_col >= merge_start_col:
                worksheet.merge_range(merge_start_row, merge_start_col, merge_end_row, merge_end_col, value, header_format)
        except Exception:
            # Skip invalid merge ranges
            pass

    # Format header row (default)
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(start_row, col_num, value, header_format)

    # Write data rows
    for row_num in range(len(df)):
        for col_num in range(len(df.columns)):
            value = df.iloc[row_num, col_num]
            worksheet.write(start_row + row_num + 1, col_num, value)

    # Apply cell borders if provided
    cell_borders = formatting.get('cell_borders', {})
    for cell_key, borders in cell_borders.items():
        try:
            row_str, col_str = cell_key.split(',')
            row = int(row_str) + start_row + 1  # +start_row for table position, +1 for header
            col = int(col_str)

            # Get cell value
            if row - start_row - 1 < len(df) and col < len(df.columns):
                cell_value = df.iloc[row - start_row - 1, col]

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
                row = row + start_row + 1  # +start_row for table position, +1 for header

                # Get cell value
                if row - start_row - 1 < len(df) and col < len(df.columns):
                    cell_value = df.iloc[row - start_row - 1, col]
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
