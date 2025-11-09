"""
Gemini (Google) provider for table extraction.
"""

import time
import json
from typing import Optional, Dict, Any
import google.generativeai as genai
from PIL import Image
import io
from core.providers.base import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini provider for Vision API table extraction."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        genai.configure(api_key=api_key)
        self.text_model = genai.GenerativeModel('gemini-1.5-flash')
        self.vision_model = genai.GenerativeModel('gemini-1.5-pro')  # BEST for vision
        self.name = "Gemini"

    def _get_pricing(self):
        """Gemini 1.5 Pro pricing in EUR (vision model)"""
        return {
            'input': 1.21,    # ~$1.25 per 1M tokens for Pro
            'output': 4.4     # ~$5 per 1M tokens for Pro
        }

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract table data from image using Gemini 1.5 Pro Vision API.

        Args:
            image_bytes: Image bytes (PNG/JPEG)
            context: Optional context

        Returns:
            Dict with rows, metadata, success
        """
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))

        prompt = """Extract ALL data from ALL tables in this image AND detect the visual table structure.

STEP 1 - Find all tables:
- Look for ALL tables/sections on this page (there may be 1, 2, 3, or more distinct tables)
- Identify if tables have section headers (blue/colored headers above table)
- Count how many distinct tables you see
- Note: Some documents have multiple tables stacked vertically (e.g., summary table + daily calendar table)

STEP 2 - For EACH table separately:
- Extract the section title/header if present (text above the table, often in colored background)
- Identify ALL column headers for THIS table
- Extract EVERY row from THIS table
- Extract EVERY cell value that is visible
- If a cell is blank or unreadable, write "UNREADABLE"
- For dates: format as dd.mm.yyyy
- For numbers: round to 2 decimals

STEP 3 - Keep tables SEPARATE:
- DO NOT combine rows from different tables
- Each table should be a separate object in the "tables" array
- Preserve the vertical order (top table first, bottom table second, etc.)

STEP 5 - Detect table VISUAL STRUCTURE (borders, merged cells):
- Merged cells: Identify any cells that span multiple columns or rows (common in headers)
- Cell borders: For each cell, detect which borders are visible (top, bottom, left, right)
- Header rows: Identify which row indices contain headers (often row 0, but may be multiple)
- Total rows: Identify rows containing totals/sums (often labeled "Kokku", "Total", "Summa")
- Bold cells: Identify cells with bold or emphasized text

STEP 6 - CRITICAL: Small Number Accuracy

PAY EXTRA ATTENTION to small numbers in narrow cells:

1. DISTINGUISH "0" vs "8" carefully:
   - "8" has TWO loops stacked vertically with a horizontal line in the middle
   - "0" is ONE oval/circle with NO middle division
   - If uncertain, look at the MIDDLE of the character - does it have a horizontal stroke?

2. Calendar/Daily columns (numbered 1-31):
   - These contain hours worked per day - ACCURACY IS CRITICAL
   - Common values: "0", "8", "OFF", "ON", blank
   - Empty cells = blank (not "0")
   - Zoom in mentally before reading small numbers

3. When uncertain between "0" and "8":
   - Mark as "UNREADABLE" rather than guessing
   - Better to flag uncertainty than provide wrong data

4. For ALL single-digit numbers in narrow columns:
   - Double-check your reading
   - Verify the character shape matches the value

Return ONLY valid JSON (no markdown, no explanations):
{
  "tables": [
    {
      "section_title": "Effort for Normal Working Hours (h)",
      "columns": ["Service Request", "Contractual Days", "Available Days"],
      "rows": [
        {"Service Request": "SR2-WP2", "Contractual Days": "5", "Available Days": "3"},
        {"Service Request": "Totals", "Contractual Days": "10", "Available Days": "5"}
      ],
      "formatting": {
        "merged_cells": [{"start_row": 0, "start_col": 0, "end_row": 0, "end_col": 2, "value": "Header"}],
        "cell_borders": {"0,0": {"top": true, "bottom": true, "left": true, "right": true}},
        "header_rows": [0],
        "total_rows": [1],
        "bold_cells": [[0, 0], [1, 0]]
      }
    },
    {
      "section_title": null,
      "columns": ["Service Request", "1", "2", "3", "4", "5"],
      "rows": [
        {"Service Request": "SR2-WP2", "1": "0", "2": "8", "3": "8", "4": "0", "5": "8"},
        {"Service Request": "Totals", "1": "0", "2": "8", "3": "8", "4": "0", "5": "8"}
      ],
      "formatting": {
        "header_rows": [0],
        "bold_cells": [[1, 0]]
      }
    }
  ],
  "metadata": {
    "tables_found": 2,
    "total_rows": 4,
    "page_sections": 2
  }
}

CRITICAL:
- You MUST return at least one row for each table you find
- If you see 2 tables, return 2 separate objects in "tables" array
- Do NOT combine tables - keep them separate
- Cell borders: Only include cells that have visible borders (skip cells without borders to save space)
- Row/column indices: Use 0-based indexing within each table (first row is 0, first column is 0)
- If section_title is not visible/applicable, use null
"""

        start_time = time.time()

        try:
            response = self.vision_model.generate_content(
                [prompt, image],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                )
            )

            latency = time.time() - start_time

            # Extract token usage
            input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
            output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0

            self._track_call(latency, input_tokens, output_tokens)

            # Parse JSON response
            content = response.text

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                # JSON parsing failed - return error with raw response for debugging
                latency = time.time() - start_time
                self._track_call(latency)
                return {
                    'columns': [],
                    'rows': [],
                    'metadata': {
                        'error': f'JSON parsing failed: {str(e)}',
                        'raw_response': content[:500]  # First 500 chars for debugging
                    },
                    'formatting': {},
                    'success': False
                }

            # Extract tables array (new format)
            tables = result.get('tables', [])
            metadata = result.get('metadata', {})

            # Legacy compatibility: flatten tables into single rows/columns/formatting
            all_rows = []
            all_columns = []
            combined_formatting = {
                'merged_cells': [],
                'cell_borders': {},
                'header_rows': [],
                'total_rows': [],
                'bold_cells': []
            }

            row_offset = 0
            for table in tables:
                table_rows = table.get('rows', [])
                table_columns = table.get('columns', [])
                table_formatting = table.get('formatting', {})

                # Collect rows
                all_rows.extend(table_rows)

                # Collect unique columns
                for col in table_columns:
                    if col not in all_columns:
                        all_columns.append(col)

                # Merge formatting with row offset
                if table_formatting.get('merged_cells'):
                    for merge in table_formatting['merged_cells']:
                        merged_copy = merge.copy()
                        merged_copy['start_row'] += row_offset
                        merged_copy['end_row'] += row_offset
                        combined_formatting['merged_cells'].append(merged_copy)

                if table_formatting.get('cell_borders'):
                    for cell_key, borders in table_formatting['cell_borders'].items():
                        row_str, col_str = cell_key.split(',')
                        new_row = int(row_str) + row_offset
                        new_key = f"{new_row},{col_str}"
                        combined_formatting['cell_borders'][new_key] = borders

                if table_formatting.get('header_rows'):
                    for hr in table_formatting['header_rows']:
                        combined_formatting['header_rows'].append(hr + row_offset)

                if table_formatting.get('total_rows'):
                    for tr in table_formatting['total_rows']:
                        combined_formatting['total_rows'].append(tr + row_offset)

                if table_formatting.get('bold_cells'):
                    for cell in table_formatting['bold_cells']:
                        combined_formatting['bold_cells'].append([cell[0] + row_offset, cell[1]])

                row_offset += len(table_rows)

            # Update metadata with total counts
            if 'total_columns' not in metadata:
                metadata['total_columns'] = len(all_columns)
            if 'total_rows' not in metadata:
                metadata['total_rows'] = len(all_rows)

            return {
                'tables': tables,  # NEW: Separate tables
                'columns': all_columns,  # LEGACY: Flattened
                'rows': all_rows,  # LEGACY: Flattened
                'metadata': metadata,
                'formatting': combined_formatting,  # LEGACY: Combined
                'success': True
            }

        except Exception as e:
            latency = time.time() - start_time
            self._track_call(latency)
            return {
                'columns': [],
                'rows': [],
                'metadata': {'error': str(e)},
                'formatting': {},
                'success': False
            }
