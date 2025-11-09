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
        self.vision_model = "gpt-4o-2024-08-06"  # Structured Outputs support
        self.use_structured_outputs = True  # Enable by default

    def _get_pricing(self):
        """GPT-4o pricing in EUR (vision model is more expensive)"""
        return {
            'input': 4.4,    # ~$5 per 1M tokens for GPT-4o
            'output': 13.2   # ~$15 per 1M tokens for GPT-4o
        }

    @classmethod
    def get_default_prompt(cls) -> str:
        """Return default OpenAI Vision API prompt."""
        return """Extract ALL data from this GWB Monthly Time Sheet document.

This document has 5 main sections that you MUST extract:

1. SERVICE PROVIDER DETAILS (blue header section):
   - Service Provider (name)
   - Service Provider Start Date
   - Type
   - Profile
   - Place of Delivery

2. CONTRACT INFORMATION (blue header section):
   - Specific Contract Number
   - Specific Contract Start/End Dates
   - Lot No
   - Contractor Name
   - Framework Contract Number
   - Program

3. TIMESHEET DETAILS (blue header section):
   - Service Request Number
   - Service Request Start/End Dates

4. SUMMARY TABLE (Effort for Normal Working Hours):
   - All rows with Contractual/Available/Consumed/Remaining Days

5. DAILY CALENDAR (days 1-31):
   - Hours worked per day (0, 8, OFF, ON, etc.)

CRITICAL INSTRUCTIONS:
- Extract data from ALL 5 sections above
- For blue header sections: Look for key-value pairs (Label: Value)
- For tables: Extract all rows and columns
- If a field is not found, use "NOT_FOUND" instead of omitting it
- Pay attention to small numbers (distinguish "0" vs "8" carefully)

The response will be automatically structured according to the defined JSON schema."""

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        use_structured_outputs: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Extract table data from image using GPT-4o Vision API with Structured Outputs.

        Args:
            image_bytes: Image bytes (PNG/JPEG)
            context: Optional context
            custom_prompt: Optional custom prompt (overrides default)
            use_structured_outputs: Whether to use Structured Outputs API (default: True)

        Returns:
            Dict with rows, metadata, success
        """
        # Encode image to base64
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')

        # Determine prompt and structured outputs mode
        prompt = custom_prompt if custom_prompt else self.get_default_prompt()
        use_structured = use_structured_outputs if use_structured_outputs is not None else self.use_structured_outputs

        start_time = time.time()

        try:
            if use_structured:
                # NEW: Use Structured Outputs API for 100% schema adherence
                from core.schemas.gwb_timesheet import GWBTimesheet

                response = self.client.beta.chat.completions.parse(
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
                    response_format=GWBTimesheet,
                    temperature=0.0
                )

                latency = time.time() - start_time

                # Extract token usage
                usage = response.usage
                input_tokens = usage.prompt_tokens if usage else 0
                output_tokens = usage.completion_tokens if usage else 0

                self._track_call(latency, input_tokens, output_tokens)

                # Parse Pydantic model
                timesheet = response.choices[0].message.parsed

                # Convert to legacy format for backward compatibility
                return self._convert_structured_to_legacy(timesheet)

            else:
                # LEGACY: Fallback to non-structured mode (not implemented yet)
                return {
                    'columns': [],
                    'rows': [],
                    'metadata': {'error': 'Structured Outputs disabled - use use_structured_outputs=True'},
                    'formatting': {},
                    'success': False
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

    # LEGACY CODE MOVED TO ARCHIVE (lines 143-381)
    # Old prompt-based extraction - replaced by Structured Outputs
    # Kept here for reference but not in use:
    def _legacy_extract(self):
        """
        Legacy extraction method - DEPRECATED.
        Replaced by Structured Outputs API.
        """
        # Old implementation with prompt-based JSON parsing
        # See git history for full code
        pass

    def _convert_structured_to_legacy(self, timesheet) -> Dict[str, Any]:
        """
        Convert Pydantic GWBTimesheet model to legacy format.

        This ensures backward compatibility with existing XLSX export code.
        """
        from core.schemas.gwb_timesheet import GWBTimesheet

        # Create metadata section as first "table"
        metadata_rows = []

        # SERVICE PROVIDER DETAILS
        spd = timesheet.service_provider_details
        metadata_rows.extend([
            {"Section": "SERVICE PROVIDER DETAILS", "Field": "Service Provider", "Value": spd.service_provider},
            {"Section": "SERVICE PROVIDER DETAILS", "Field": "Start Date", "Value": spd.service_provider_start_date},
            {"Section": "SERVICE PROVIDER DETAILS", "Field": "Type", "Value": spd.type},
            {"Section": "SERVICE PROVIDER DETAILS", "Field": "Profile", "Value": spd.profile},
            {"Section": "SERVICE PROVIDER DETAILS", "Field": "Place of Delivery", "Value": spd.place_of_delivery},
        ])

        # CONTRACT INFORMATION
        ci = timesheet.contract_information
        metadata_rows.extend([
            {"Section": "CONTRACT INFORMATION", "Field": "Contract Number", "Value": ci.specific_contract_number},
            {"Section": "CONTRACT INFORMATION", "Field": "Start Date", "Value": ci.specific_contract_start_date},
            {"Section": "CONTRACT INFORMATION", "Field": "End Date", "Value": ci.specific_contract_end_date},
            {"Section": "CONTRACT INFORMATION", "Field": "Lot No", "Value": ci.lot_no},
            {"Section": "CONTRACT INFORMATION", "Field": "Contractor", "Value": ci.contractor_name},
            {"Section": "CONTRACT INFORMATION", "Field": "Framework Contract", "Value": ci.framework_contract_number},
            {"Section": "CONTRACT INFORMATION", "Field": "Program", "Value": ci.program},
        ])

        # TIMESHEET DETAILS
        td = timesheet.timesheet_details
        metadata_rows.extend([
            {"Section": "TIMESHEET DETAILS", "Field": "Service Request Number", "Value": td.service_request_number},
            {"Section": "TIMESHEET DETAILS", "Field": "Start Date", "Value": td.service_request_start_date},
            {"Section": "TIMESHEET DETAILS", "Field": "End Date", "Value": td.service_request_end_date},
        ])

        # Summary table rows
        summary_rows = [row.model_dump() for row in timesheet.summary_table.rows]

        # Daily calendar rows
        daily_rows = [row.model_dump() for row in timesheet.daily_calendar.rows]

        # Build tables array (new format)
        tables = [
            {
                "section_title": "DOCUMENT METADATA",
                "columns": ["Section", "Field", "Value"],
                "rows": metadata_rows,
                "formatting": {}
            },
            {
                "section_title": timesheet.summary_table.section_title,
                "columns": list(summary_rows[0].keys()) if summary_rows else [],
                "rows": summary_rows,
                "formatting": {}
            },
            {
                "section_title": timesheet.daily_calendar.section_title or "Daily Calendar",
                "columns": list(daily_rows[0].keys()) if daily_rows else [],
                "rows": daily_rows,
                "formatting": {}
            }
        ]

        # Flatten for legacy compatibility
        all_rows = metadata_rows + summary_rows + daily_rows
        all_columns = ["Section", "Field", "Value"]  # Metadata columns first

        return {
            'tables': tables,  # NEW: Separate tables
            'columns': all_columns,  # LEGACY
            'rows': all_rows,  # LEGACY
            'metadata': {
                'tables_found': 3,
                'total_rows': len(all_rows),
                'extraction_method': 'structured_outputs'
            },
            'formatting': {},  # LEGACY
            'success': True
        }
