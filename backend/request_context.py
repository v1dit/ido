from __future__ import annotations

import asyncio
from dataclasses import dataclass

from shared.ir import EngineeringIR


@dataclass(frozen=True)
class RequestContext:
    prompt: str | None
    target_tool: str | None
    ir: EngineeringIR | None = None
    inference_provider: str | None = None


class RequestContextStore:
    """Remember prompt and IR metadata so execution exports stay complete."""

    def __init__(self) -> None:
        self._contexts: dict[str, RequestContext] = {}
        self._lock = asyncio.Lock()

    async def set(
        self,
        request_id: str,
        *,
        prompt: str | None,
        target_tool: str | None,
        ir: EngineeringIR | None = None,
        inference_provider: str | None = None,
    ) -> None:
        async with self._lock:
            self._contexts[request_id] = RequestContext(
                prompt=prompt,
                target_tool=target_tool,
                ir=ir,
                inference_provider=inference_provider,
            )

    async def get(self, request_id: str) -> RequestContext | None:
        async with self._lock:
            return self._contexts.get(request_id)
