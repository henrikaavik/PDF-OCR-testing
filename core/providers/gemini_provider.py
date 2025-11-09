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
        self.use_structured_outputs = False  # Gemini doesn't support Structured Outputs

    def _get_pricing(self):
        """Gemini 1.5 Pro pricing in EUR (vision model)"""
        return {
            'input': 1.21,    # ~$1.25 per 1M tokens for Pro
            'output': 4.4     # ~$5 per 1M tokens for Pro
        }

    @classmethod
    def get_default_prompt(cls) -> str:
        """Return default Gemini Vision API prompt with universal schema."""
        return """Extract ALL data from this GWB Monthly Time Sheet document in structured JSON format.

IMPORTANT: This document has 5 main sections - you MUST extract data from ALL of them:

SECTION 1: SERVICE PROVIDER DETAILS (blue header box)
Extract these fields:
- service_provider (name)
- service_provider_start_date (dd/mm/yyyy)
- type (e.g., QTM, GTM)
- profile (job title/role)
- place_of_delivery (location)

SECTION 2: CONTRACT INFORMATION (blue header box)
Extract these fields:
- specific_contract_number
- specific_contract_start_date (dd/mm/yyyy)
- specific_contract_end_date (dd/mm/yyyy)
- lot_no
- contractor_name (company)
- framework_contract_number
- program (program name)

SECTION 3: TIMESHEET DETAILS (blue header box)
Extract these fields:
- service_request_number (e.g., SR2)
- service_request_start_date (dd/mm/yyyy)
- service_request_end_date (dd/mm/yyyy)

SECTION 4: SUMMARY TABLE (Effort for Normal Working Hours)
Extract ALL rows with columns:
- service_request
- contractual_days_onsite, contractual_days_offsite
- available_days_onsite, available_days_offsite
- consumed_days_onsite, consumed_days_offsite
- remaining_days_onsite, remaining_days_offsite

SECTION 5: DAILY CALENDAR (days 1-31)
Extract ALL rows with columns:
- service_request
- day_1, day_2, day_3, ... day_31 (hours: 0, 8, OFF, ON, or empty)

CRITICAL RULES:
1. If a field is not found or unreadable, use "NOT_FOUND" instead of omitting it
2. For small numbers (0 vs 8): "8" has TWO loops with middle line, "0" is ONE oval
3. Empty calendar cells should be null, not "0"
4. Extract data from ALL 5 sections - do not skip any section

Return valid JSON ONLY (no markdown, no explanations):
{
  "service_provider_details": {
    "service_provider": "...",
    "service_provider_start_date": "...",
    "type": "...",
    "profile": "...",
    "place_of_delivery": "..."
  },
  "contract_information": {
    "specific_contract_number": "...",
    "specific_contract_start_date": "...",
    "specific_contract_end_date": "...",
    "lot_no": "...",
    "contractor_name": "...",
    "framework_contract_number": "...",
    "program": "..."
  },
  "timesheet_details": {
    "service_request_number": "...",
    "service_request_start_date": "...",
    "service_request_end_date": "..."
  },
  "summary_table": {
    "section_title": "Effort for Normal Working Hours (h)",
    "rows": [
      {"service_request": "...", "contractual_days_onsite": "...", ...}
    ]
  },
  "daily_calendar": {
    "section_title": null,
    "rows": [
      {"service_request": "...", "day_1": "...", "day_2": "...", ...}
    ]
  }
}"""

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        use_structured_outputs: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Extract table data from image using Gemini 1.5 Pro Vision API.

        Args:
            image_bytes: Image bytes (PNG/JPEG)
            context: Optional context
            custom_prompt: Optional custom prompt (overrides default)
            use_structured_outputs: Ignored (Gemini doesn't support Structured Outputs)

        Returns:
            Dict with rows, metadata, success
        """
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))

        # Use custom prompt or default
        prompt = custom_prompt if custom_prompt else self.get_default_prompt()

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
