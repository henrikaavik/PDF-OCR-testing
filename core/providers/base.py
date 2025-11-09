"""
Base AI provider interface for PDF table extraction using Vision APIs.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


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
    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract tables from PDF page image using Vision API.

        Args:
            image_bytes: Image bytes (PDF page as PNG/JPEG)
            context: Optional context (filename, page number, etc.)

        Returns:
            Dictionary with:
            - tables: List of table objects, each with:
                - section_title: Optional section header text
                - columns: List of column names
                - rows: List of dicts with extracted data
                - formatting: Dict with visual structure for this table
            - metadata: Dict with tables_found, total_rows, etc.
            - success: Boolean

            LEGACY COMPATIBILITY:
            - rows: Flattened list of all rows (for backward compatibility)
            - columns: Combined list of all unique columns
            - formatting: Combined formatting metadata

        Formatting Dictionary (optional):
            - merged_cells: List of merged cell ranges
            - cell_borders: Dict mapping "row,col" to border info
            - header_rows: List of row indices that are headers
            - total_rows: List of row indices that contain totals
            - bold_cells: List of [row, col] coordinates for bold cells
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
        Track API call for cost and performance monitoring.

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
            - total_cost_eur: Total cost in EUR
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
    Placeholder provider - Vision API is required.
    """

    def __init__(self):
        super().__init__(api_key=None)
        self.name = "No AI Provider"

    def extract_table_from_image(
        self,
        image_bytes: bytes,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Not available without AI provider."""
        return {
            'rows': [],
            'columns': [],
            'metadata': {'warning': 'Vision API required - no AI provider configured'},
            'formatting': {},
            'success': False
        }


def create_provider(provider_name: str, api_key: Optional[str] = None) -> AIProvider:
    """
    Factory function to create AI provider instances.

    Args:
        provider_name: Name of the provider ("openai", "grok", "kimi", "gemini")
        api_key: API key for the provider

    Returns:
        AIProvider instance

    Raises:
        ValueError: If provider name is not recognized
    """
    if provider_name.lower() == "openai" or provider_name.lower() == "chatgpt":
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
