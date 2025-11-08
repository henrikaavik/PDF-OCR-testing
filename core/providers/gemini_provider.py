"""
Gemini (Google) provider for table normalization.
"""

import time
import json
from typing import Optional, Dict, Any
import pandas as pd
import google.generativeai as genai
from PIL import Image
import io
from core.providers.base import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

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

    def normalize_table(
        self,
        raw_table: pd.DataFrame,
        context: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Normalize table using Gemini.

        Args:
            raw_table: Raw DataFrame
            context: Optional context

        Returns:
            Normalized DataFrame
        """
        if raw_table.empty:
            return raw_table

        # Build prompt
        table_str = raw_table.to_string()
        prompt = f"""Normalize this work-hour table to have exactly these columns:
- Kuupäev (date in dd.mm.yyyy format)
- Töötaja (employee name)
- Projekt (project name)
- Tunnid (hours as number)

Input table:
{table_str}

Return ONLY the normalized data as CSV format with headers. Do not include any explanations."""

        start_time = time.time()

        try:
            response = self.text_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                )
            )

            latency = time.time() - start_time

            # Extract token usage
            input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
            output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0

            self._track_call(latency, input_tokens, output_tokens)

            # Parse response
            content = response.text

            # Try to parse as CSV
            from io import StringIO
            try:
                normalized = pd.read_csv(StringIO(content))
                return normalized
            except:
                return raw_table

        except Exception as e:
            latency = time.time() - start_time
            self._track_call(latency)
            return raw_table

    def enhance_ocr_text(
        self,
        ocr_text: str,
        context: Optional[str] = None
    ) -> str:
        """
        Enhance OCR text using Gemini.

        Args:
            ocr_text: Raw OCR text
            context: Optional context

        Returns:
            Enhanced text
        """
        if not ocr_text or len(ocr_text) < 10:
            return ocr_text

        prompt = f"""Clean up this OCR-extracted text from a work-hour table. Fix obvious OCR errors but preserve the table structure:

{ocr_text}

Return the cleaned text without explanations."""

        start_time = time.time()

        try:
            response = self.text_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.0,
                )
            )

            latency = time.time() - start_time

            # Extract token usage
            input_tokens = response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0
            output_tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0

            self._track_call(latency, input_tokens, output_tokens)

            enhanced = response.text
            return enhanced

        except Exception as e:
            latency = time.time() - start_time
            self._track_call(latency)
            return ocr_text

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract work hours table from image using Gemini 1.5 Pro Vision.

        Args:
            image_bytes: Image bytes (PNG/JPEG)
            context: Optional context

        Returns:
            Dict with rows, metadata, success
        """
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))

        prompt = """Analyze this image and find ALL tables present. Extract data from EVERY table you see.

CRITICAL RULES:
1. Find ALL tables on this page/image (there may be multiple tables)
2. For each table, identify ALL column headers
3. Extract EVERY cell value that is CLEARLY VISIBLE from ALL tables
4. If a cell is UNREADABLE or BLANK, use "UNREADABLE" as the value
5. If you can CALCULATE a missing value from other visible data (e.g., sum total), you MAY calculate it
6. NEVER invent or guess data that isn't visible or calculable
7. Combine rows from ALL tables into one list (preserve column structure)
8. For dates: use format dd.mm.yyyy (convert if needed)
9. For numbers: use numeric values, rounded to 2 decimals

Return ONLY this JSON structure (no explanations):
{
  "columns": ["Column1", "Column2", "Column3", ...],
  "rows": [
    {"Column1": "value1", "Column2": "value2", "Column3": "value3", ...},
    {"Column1": "value1", "Column2": "value2", "Column3": "value3", ...}
  ],
  "metadata": {
    "calculated_fields": [],
    "unreadable_fields": [],
    "warnings": [],
    "total_columns": 0,
    "total_rows": 0,
    "tables_found": 0
  }
}

IMPORTANT:
- If multiple tables have different columns, include ALL unique columns in the "columns" array
- For rows from tables that don't have certain columns, use "UNREADABLE" for missing columns
- Extract ALL columns from ALL tables
- Each row must have values for ALL columns (use "UNREADABLE" for columns not present in that table)
- If you calculated a field, add "row_X_column_name" to calculated_fields
- If a field was unreadable, add "row_X_column_name" to unreadable_fields
- Set "tables_found" to the number of distinct tables you found on this page
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

            result = json.loads(content)

            # Update metadata with total counts
            metadata = result.get('metadata', {})
            columns = result.get('columns', [])
            rows = result.get('rows', [])

            if 'total_columns' not in metadata:
                metadata['total_columns'] = len(columns)
            if 'total_rows' not in metadata:
                metadata['total_rows'] = len(rows)

            return {
                'columns': columns,
                'rows': rows,
                'metadata': metadata,
                'success': True
            }

        except Exception as e:
            latency = time.time() - start_time
            self._track_call(latency)
            return {
                'columns': [],
                'rows': [],
                'metadata': {'error': str(e)},
                'success': False
            }
