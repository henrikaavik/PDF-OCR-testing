"""
Grok (xAI) provider for table extraction.
Uses OpenAI-compatible API.
"""

import time
from typing import Optional, Dict, Any
from openai import OpenAI
from core.providers.base import AIProvider


class GrokProvider(AIProvider):
    """xAI Grok provider for Vision API table extraction."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        # Grok uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )
        self.name = "Grok"
        self.model = "grok-beta"

    def _get_pricing(self):
        """Grok pricing in EUR (converted from USD ~1.1)"""
        return {
            'input': 4.4,    # ~$5 per 1M tokens
            'output': 13.2   # ~$15 per 1M tokens
        }

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Grok vision support - placeholder."""
        return {
            'rows': [],
            'metadata': {'warning': 'Grok vision API not yet implemented'},
            'success': False
        }
