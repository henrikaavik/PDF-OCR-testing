"""
Gemini (Google) provider for table normalization.
"""

import time
from typing import Optional
import pandas as pd
import google.generativeai as genai
from core.providers.base import AIProvider


class GeminiProvider(AIProvider):
    """Google Gemini provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.name = "Gemini"

    def _get_pricing(self):
        """Gemini 1.5 Flash pricing in EUR (converted from USD ~1.1)"""
        return {
            'input': 0.033,   # ~$0.035 per 1M tokens (up to 128k context)
            'output': 0.11    # ~$0.12 per 1M tokens
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
            response = self.model.generate_content(
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
            response = self.model.generate_content(
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
