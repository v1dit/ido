from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.sponsor_insights import scene_snapshot
from shared.contracts import TraceEvent
from shared.ir import EngineeringIR

logger = logging.getLogger("cad_agent.airbyte")


@dataclass(frozen=True)
class AirbyteExportResult:
    exported: bool
    records: int = 0
    error: str | None = None


class AirbyteContextExporter:
    """Export CAD-Agent context records for Airbyte ingestion (JSONL + optional HTTP)."""

    def __init__(
        self,
        *,
        context_dir: str | None,
        endpoint: str | None,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._context_dir = Path(context_dir).expanduser() if context_dir else None
        self._endpoint = endpoint.rstrip("/") if endpoint else None
        self._api_key = api_key
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._context_dir or self._endpoint)

    async def export(
        self,
        *,
        request_id: str,
        event_type: str,
        prompt: str | None = None,
        target_tool: str | None = None,
        ir: EngineeringIR | None = None,
        trace: list[TraceEvent] | None = None,
        execution_status: str | None = None,
    ) -> AirbyteExportResult:
        if not self.enabled:
            return AirbyteExportResult(exported=False)

        record = {
            "request_id": request_id,
            "event_type": event_type,
            "prompt": prompt,
            "target_tool": target_tool,
            "execution_status": execution_status,
            "scene_summary": scene_snapshot(
                prompt=prompt,
                ir=ir,
                target_tool=target_tool,
            ),
            "ir": ir.model_dump(mode="json") if ir is not None else None,
            "trace": [event.model_dump(mode="json") for event in (trace or [])],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
        line = json.dumps(record, separators=(",", ":"), sort_keys=True)

        try:
            if self._context_dir is not None:
                await asyncio.to_thread(self._append_jsonl, line)
            if self._endpoint is not None:
                await asyncio.to_thread(self._post_record, record)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.warning("airbyte context export failed for %s: %s", request_id, exc)
            return AirbyteExportResult(exported=False, error=str(exc))

        logger.info(
            "airbyte context exported request_id=%s event_type=%s",
            request_id,
            event_type,
        )
        return AirbyteExportResult(exported=True, records=1)

    def _append_jsonl(self, line: str) -> None:
        assert self._context_dir is not None
        self._context_dir.mkdir(parents=True, exist_ok=True)
        path = self._context_dir / "cad_agent_context.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.write("\n")

    def _post_record(self, record: dict[str, Any]) -> None:
        assert self._endpoint is not None
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = Request(
            self._endpoint,
            data=json.dumps(record).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        with urlopen(request, timeout=self._timeout) as response:
            if getattr(response, "status", 200) >= 400:
                raise HTTPError(
                    self._endpoint,
                    response.status,
                    response.reason,
                    response.headers,
                    None,
                )


class NullAirbyteContextExporter(AirbyteContextExporter):
    def __init__(self) -> None:
        super().__init__(context_dir=None, endpoint=None)

    @property
    def enabled(self) -> bool:
        return False

    async def export(self, **_kwargs) -> AirbyteExportResult:
        return AirbyteExportResult(exported=False)


def create_airbyte_exporter(settings: Any) -> AirbyteContextExporter:
    if not settings.airbyte_enabled:
        return NullAirbyteContextExporter()
    if not settings.airbyte_context_dir and not settings.airbyte_context_endpoint:
        return NullAirbyteContextExporter()
    return AirbyteContextExporter(
        context_dir=settings.airbyte_context_dir,
        endpoint=settings.airbyte_context_endpoint,
        api_key=settings.airbyte_api_key,
        timeout=settings.airbyte_export_timeout,
    )
