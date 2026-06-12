from __future__ import annotations

import os

from backend.providers.base import IRGenerationError
from backend.providers.openai_provider import OpenAIProvider


class PioneerProvider(OpenAIProvider):
    """Pioneer inference via the OpenAI-compatible API."""

    name = "pioneer"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client=None,
        base_url: str | None = None,
    ) -> None:
        resolved_key = api_key or os.getenv("PIONEER_API_KEY")
        if client is None and not resolved_key:
            raise IRGenerationError("PIONEER_API_KEY is not configured")
        super().__init__(
            api_key=resolved_key,
            model=model or os.getenv("PIONEER_MODEL_ID", "gpt-4o"),
            client=client,
            base_url=base_url or os.getenv("PIONEER_BASE_URL", "https://api.pioneer.ai/v1"),
        )
