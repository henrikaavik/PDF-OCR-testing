"""
Kimi (Moonshot AI) provider for table extraction.
Uses OpenAI-compatible API.
"""

import time
from typing import Optional, Dict, Any
from openai import OpenAI
from core.providers.base import AIProvider


class KimiProvider(AIProvider):
    """Moonshot AI Kimi provider for Vision API table extraction."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        # Kimi uses OpenAI-compatible API
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.moonshot.cn/v1"
        )
        self.name = "Kimi"
        self.model = "moonshot-v1-8k"

    def _get_pricing(self):
        """Kimi pricing in EUR (converted from CNY ~0.13)"""
        return {
            'input': 1.56,   # ~12 CNY per 1M tokens
            'output': 1.56   # ~12 CNY per 1M tokens
        }

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Kimi vision support - placeholder."""
        return {
            'rows': [],
            'metadata': {'warning': 'Kimi vision API not yet implemented'},
            'success': False
        }
