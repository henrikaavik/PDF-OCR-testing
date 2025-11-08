"""
OpenAI (ChatGPT) provider for table extraction.
"""

import time
import base64
import json
from typing import Optional, Dict, Any
from openai import OpenAI
from core.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT provider for Vision API table extraction."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = OpenAI(api_key=api_key)
        self.name = "ChatGPT"
        self.text_model = "gpt-4o-mini"
        self.vision_model = "gpt-4o"  # BEST vision model

    def _get_pricing(self):
        """GPT-4o pricing in EUR (vision model is more expensive)"""
        return {
            'input': 4.4,    # ~$5 per 1M tokens for GPT-4o
            'output': 13.2   # ~$15 per 1M tokens for GPT-4o
        }

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract table data from image using GPT-4o Vision API.

        Args:
            image_bytes: Image bytes (PNG/JPEG)
            context: Optional context

        Returns:
            Dict with rows, metadata, success
        """
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        prompt = """Extract ALL data from ALL tables in this image AND detect the visual table structure.

STEP 1 - Find all tables:
- Look for ALL tables on this page (there may be 1, 2, 3, or more tables)
- Count how many distinct tables you see

STEP 2 - Extract column headers:
- For each table, identify ALL column headers
- Combine all unique column names from all tables

STEP 3 - Extract all rows:
- For EACH table, extract EVERY row
- Extract EVERY cell value that is visible
- If a cell is blank or unreadable, write "UNREADABLE"
- Combine all rows from all tables into one list

STEP 4 - Format each row:
- Each row must be a dictionary with ALL column names
- If a row doesn't have a value for a column, use "UNREADABLE"
- For dates: format as dd.mm.yyyy
- For numbers: round to 2 decimals

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
  "columns": ["Col1", "Col2", "Col3"],
  "rows": [
    {"Col1": "value", "Col2": "value", "Col3": "value"},
    {"Col1": "value", "Col2": "value", "Col3": "value"}
  ],
  "metadata": {
    "tables_found": 2,
    "total_rows": 10,
    "total_columns": 3
  },
  "formatting": {
    "merged_cells": [
      {"start_row": 0, "start_col": 0, "end_row": 0, "end_col": 2, "value": "Header Text"}
    ],
    "cell_borders": {
      "0,0": {"top": true, "bottom": true, "left": true, "right": true},
      "0,1": {"top": true, "bottom": true, "left": false, "right": true}
    },
    "header_rows": [0],
    "total_rows": [10],
    "bold_cells": [[0, 0], [0, 1], [0, 2], [10, 0]]
  }
}

CRITICAL:
- You MUST return at least one row for each table you find
- If you see 2 tables, you MUST extract rows from BOTH tables
- Do NOT return empty "rows" array if you found tables
- Cell borders: Only include cells that have visible borders (skip cells without borders to save space)
- Row/column indices: Use 0-based indexing (first row is 0, first column is 0)
"""

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.0,
                max_tokens=4096
            )

            latency = time.time() - start_time

            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            self._track_call(latency, input_tokens, output_tokens)

            # Parse JSON response
            content = response.choices[0].message.content

            # Extract JSON from response (might have markdown code blocks)
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

            # Update metadata with total counts
            metadata = result.get('metadata', {})
            columns = result.get('columns', [])
            rows = result.get('rows', [])

            if 'total_columns' not in metadata:
                metadata['total_columns'] = len(columns)
            if 'total_rows' not in metadata:
                metadata['total_rows'] = len(rows)

            # Extract formatting information (optional, may not always be present)
            formatting = result.get('formatting', {})

            return {
                'columns': columns,
                'rows': rows,
                'metadata': metadata,
                'formatting': formatting,
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
