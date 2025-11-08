"""
Base AI provider interface for table normalization and header stabilization.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import time
import pandas as pd


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize provider.

        Args:
            api_key: API key for the provider
        """
        self.api_key = api_key
        self.call_count = 0
        self.total_latency = 0.0
        self.total_tokens = 0
        self.total_cost = 0.0
        self.name = self.__class__.__name__

        # Pricing per 1M tokens (input/output average)
        self.pricing = self._get_pricing()

    @abstractmethod
    def normalize_table(
        self,
        raw_table: pd.DataFrame,
        context: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Normalize a table using AI to improve header mapping and data cleanup.

        Args:
            raw_table: Raw extracted DataFrame
            context: Optional context about the document

        Returns:
            Normalized DataFrame with standardized columns
        """
        pass

    @abstractmethod
    def enhance_ocr_text(
        self,
        ocr_text: str,
        context: Optional[str] = None
    ) -> str:
        """
        Clean up and enhance OCR text using AI.

        Args:
            ocr_text: Raw OCR output
            context: Optional context

        Returns:
            Enhanced text
        """
        pass

    @abstractmethod
    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract structured work hours table directly from image using Vision API.

        This is the PREMIUM method - uses vision models to see the actual document.

        Args:
            image_bytes: Image bytes (PDF page as PNG/JPEG)
            context: Optional context (filename, etc.)

        Returns:
            Dictionary with:
            - rows: List of dicts with keys: Kuupäev, Töötaja, Projekt, Tunnid
            - metadata: Dict with warnings, calculated_fields, unreadable_fields
            - success: Boolean

        AI Instructions:
        - Extract exact data from the image
        - If a value is UNREADABLE: mark as "UNREADABLE"
        - If a value can be CALCULATED (e.g. sum from other rows):
          * Calculate it
          * Mark in metadata: {"calculated_fields": ["row_3_Tunnid"]}
        - NEVER invent data that isn't visible or calculable
        - Date format: dd.mm.yyyy
        - Hours: numeric, rounded to 2 decimals
        """
        pass

    def _get_pricing(self) -> Dict[str, float]:
        """
        Get pricing information for the provider.

        Returns:
            Dict with 'input' and 'output' prices per 1M tokens in EUR
        """
        return {'input': 0.0, 'output': 0.0}

    def _track_call(self, latency: float, input_tokens: int = 0, output_tokens: int = 0):
        """
        Track API call for benchmarking.

        Args:
            latency: Time taken for the call in seconds
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
        """
        self.call_count += 1
        self.total_latency += latency
        self.total_tokens += input_tokens + output_tokens

        # Calculate cost
        pricing = self._get_pricing()
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']
        self.total_cost += input_cost + output_cost

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get provider performance metrics.

        Returns:
            Dictionary with metrics:
            - name: Provider name
            - calls: Number of API calls
            - total_latency: Total latency in seconds
            - avg_latency: Average latency per call
            - total_tokens: Total tokens used
            - total_cost: Total cost in EUR
        """
        avg_latency = self.total_latency / self.call_count if self.call_count > 0 else 0.0

        return {
            'name': self.name,
            'calls': self.call_count,
            'total_latency': round(self.total_latency, 3),
            'avg_latency': round(avg_latency, 3),
            'total_tokens': self.total_tokens,
            'total_cost_eur': round(self.total_cost, 4)
        }

    def reset_metrics(self):
        """Reset performance metrics."""
        self.call_count = 0
        self.total_latency = 0.0
        self.total_tokens = 0
        self.total_cost = 0.0


class NoOpProvider(AIProvider):
    """
    No-operation provider for rule-based only processing.
    Does not make any AI calls.
    """

    def __init__(self):
        super().__init__(api_key=None)
        self.name = "Pole (ainult reeglid)"

    def normalize_table(
        self,
        raw_table: pd.DataFrame,
        context: Optional[str] = None
    ) -> pd.DataFrame:
        """Pass-through without AI enhancement."""
        return raw_table

    def enhance_ocr_text(
        self,
        ocr_text: str,
        context: Optional[str] = None
    ) -> str:
        """Pass-through without AI enhancement."""
        return ocr_text

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Not available without AI."""
        return {
            'rows': [],
            'metadata': {'warning': 'Vision API not available without AI provider'},
            'success': False
        }


def create_provider(provider_name: str, api_key: Optional[str] = None) -> AIProvider:
    """
    Factory function to create AI provider instances.

    Args:
        provider_name: Name of the provider ("openai", "grok", "kimi", "gemini", "none")
        api_key: API key for the provider

    Returns:
        AIProvider instance

    Raises:
        ValueError: If provider name is not recognized
    """
    if provider_name.lower() == "none" or provider_name.lower() == "pole":
        return NoOpProvider()

    elif provider_name.lower() == "openai" or provider_name.lower() == "chatgpt":
        from core.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key)

    elif provider_name.lower() == "grok":
        from core.providers.grok_provider import GrokProvider
        return GrokProvider(api_key)

    elif provider_name.lower() == "kimi":
        from core.providers.kimi_provider import KimiProvider
        return KimiProvider(api_key)

    elif provider_name.lower() == "gemini":
        from core.providers.gemini_provider import GeminiProvider
        return GeminiProvider(api_key)

    else:
        raise ValueError(f"Tundmatu teenusepakkuja: {provider_name}")
