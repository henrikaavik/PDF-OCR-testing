"""
OpenAI (ChatGPT) provider for table normalization.
"""

import time
import base64
import json
from typing import Optional, Dict, Any
import pandas as pd
from openai import OpenAI
from core.providers.base import AIProvider


class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT provider."""

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

    def normalize_table(
        self,
        raw_table: pd.DataFrame,
        context: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Normalize table using ChatGPT.

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
            response = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": "You are a data normalization assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )

            latency = time.time() - start_time

            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            self._track_call(latency, input_tokens, output_tokens)

            # Parse response
            content = response.choices[0].message.content

            # Try to parse as CSV
            from io import StringIO
            try:
                normalized = pd.read_csv(StringIO(content))
                return normalized
            except:
                # If parsing fails, return original
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
        Enhance OCR text using ChatGPT.

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
            response = self.client.chat.completions.create(
                model=self.text_model,
                messages=[
                    {"role": "system", "content": "You are an OCR cleanup assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )

            latency = time.time() - start_time

            # Extract token usage
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            self._track_call(latency, input_tokens, output_tokens)

            enhanced = response.choices[0].message.content
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
        Extract work hours table from image using GPT-4o Vision API.

        Args:
            image_bytes: Image bytes (PNG/JPEG)
            context: Optional context

        Returns:
            Dict with rows, metadata, success
        """
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        prompt = """Analyze this table/timesheet image and extract the COMPLETE table structure with ALL columns and rows.

CRITICAL RULES:
1. First identify ALL column headers in the table
2. Extract EVERY cell value that is CLEARLY VISIBLE
3. If a cell is UNREADABLE or BLANK, use "UNREADABLE" as the value
4. If you can CALCULATE a missing value from other visible data (e.g., sum total), you MAY calculate it
5. NEVER invent or guess data that isn't visible or calculable
6. Preserve the exact table structure (all columns, all rows)
7. For dates: use format dd.mm.yyyy (convert if needed)
8. For numbers: use numeric values, rounded to 2 decimals

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
    "total_rows": 0
  }
}

IMPORTANT:
- Extract ALL columns you see, not just specific fields
- Each row must have values for ALL columns (use "UNREADABLE" for empty/unclear cells)
- If you calculated a field, add "row_X_column_name" to calculated_fields
- If a field was unreadable, add "row_X_column_name" to unreadable_fields
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
