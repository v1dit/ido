from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from shared.contracts import TraceEvent

logger = logging.getLogger("cad_agent.guild")

STEP_ORDER = ("parse", "validate", "route", "execute")


@dataclass(frozen=True)
class GuildExportResult:
    exported: bool
    trace_view_url: str | None = None
    error: str | None = None


class GuildTraceExporter:
    def __init__(
        self,
        *,
        otlp_endpoint: str,
        api_key: str | None,
        workspace_id: str | None,
        trace_view_url_template: str,
        service_name: str = "cad-agent-api",
        timeout: float = 10.0,
    ) -> None:
        self._otlp_endpoint = otlp_endpoint.rstrip("/")
        self._api_key = api_key
        self._workspace_id = workspace_id
        self._trace_view_url_template = trace_view_url_template
        self._service_name = service_name
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._otlp_endpoint)

    async def export(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None = None,
        target_tool: str | None = None,
        scene_snapshot: dict[str, Any] | None = None,
    ) -> GuildExportResult:
        if not self.enabled or not events:
            return GuildExportResult(exported=False)

        payload = self._build_otlp_payload(
            request_id,
            events,
            prompt=prompt,
            target_tool=target_tool,
            scene_snapshot=scene_snapshot,
        )
        try:
            await asyncio.to_thread(self._post_otlp, payload)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.warning("guild trace export failed for %s: %s", request_id, exc)
            return GuildExportResult(
                exported=False,
                trace_view_url=self._trace_view_url(request_id),
                error=str(exc),
            )

        logger.info("guild trace exported request_id=%s events=%d", request_id, len(events))
        return GuildExportResult(
            exported=True,
            trace_view_url=self._trace_view_url(request_id),
        )

    def _trace_view_url(self, request_id: str) -> str:
        return self._trace_view_url_template.format(
            request_id=request_id,
            workspace_id=self._workspace_id or "",
        )

    def _post_otlp(self, payload: dict[str, Any]) -> None:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        request = Request(
            self._otlp_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        with urlopen(request, timeout=self._timeout) as response:
            if response.status >= 400:
                raise HTTPError(
                    self._otlp_endpoint,
                    response.status,
                    response.reason,
                    response.headers,
                    None,
                )

    def _build_otlp_payload(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None,
        target_tool: str | None,
        scene_snapshot: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        trace_id = request_id.zfill(32)[:32]
        root_span_id = self._span_id(request_id, "request")
        root_start, root_end = self._request_window(events)

        resource_attributes = [
            {"key": "service.name", "value": {"stringValue": self._service_name}},
            {"key": "cad_agent.request_id", "value": {"stringValue": request_id}},
        ]
        if self._workspace_id:
            resource_attributes.append(
                {
                    "key": "guild.workspace_id",
                    "value": {"stringValue": self._workspace_id},
                }
            )
        if target_tool:
            resource_attributes.append(
                {"key": "cad_agent.target_tool", "value": {"stringValue": target_tool}}
            )
        if prompt:
            resource_attributes.append(
                {"key": "cad_agent.prompt", "value": {"stringValue": prompt[:500]}}
            )
        if scene_snapshot:
            resource_attributes.append(
                {
                    "key": "cad_agent.object_count",
                    "value": {"stringValue": str(scene_snapshot.get("object_count", 0))},
                }
            )
            headline = scene_snapshot.get("headline")
            if headline:
                resource_attributes.append(
                    {
                        "key": "cad_agent.scene_headline",
                        "value": {"stringValue": str(headline)[:500]},
                    }
                )
            labels = scene_snapshot.get("object_labels") or []
            if labels:
                resource_attributes.append(
                    {
                        "key": "cad_agent.object_labels",
                        "value": {"stringValue": ", ".join(labels[:12])[:500]},
                    }
                )

        spans: list[dict[str, Any]] = [
            {
                "traceId": trace_id,
                "spanId": root_span_id,
                "name": "cad_agent.request",
                "kind": 1,
                "startTimeUnixNano": str(root_start),
                "endTimeUnixNano": str(root_end),
                "attributes": [
                    {"key": "cad_agent.request_id", "value": {"stringValue": request_id}},
                ],
            }
        ]

        for step in STEP_ORDER:
            step_events = [event for event in events if event.step == step]
            if not step_events:
                continue
            span = self._step_span(trace_id, request_id, step, step_events, root_span_id)
            if span is not None:
                spans.append(span)

        return {
            "resourceSpans": [
                {
                    "resource": {"attributes": resource_attributes},
                    "scopeSpans": [
                        {
                            "scope": {"name": "cad-agent.tracing", "version": "0.1.0"},
                            "spans": spans,
                        }
                    ],
                }
            ]
        }

    def _step_span(
        self,
        trace_id: str,
        request_id: str,
        step: str,
        events: list[TraceEvent],
        parent_span_id: str,
    ) -> dict[str, Any] | None:
        terminal = next(
            (event for event in reversed(events) if event.status in {"completed", "failed"}),
            None,
        )
        if terminal is None:
            return None

        start_event = next((event for event in events if event.status == "started"), events[0])
        start_ns = self._timestamp_ns(start_event.timestamp)
        duration_ns = int((terminal.duration_ms or 0) * 1_000_000)
        end_ns = start_ns + duration_ns if duration_ns else start_ns

        attributes = [
            {"key": "cad_agent.step", "value": {"stringValue": step}},
            {"key": "cad_agent.status", "value": {"stringValue": terminal.status}},
        ]
        for key, value in terminal.metadata.items():
            attributes.append(
                {
                    "key": f"cad_agent.{key}",
                    "value": {"stringValue": str(value)},
                }
            )

        return {
            "traceId": trace_id,
            "spanId": self._span_id(request_id, step),
            "parentSpanId": parent_span_id,
            "name": f"cad_agent.{step}",
            "kind": 1,
            "startTimeUnixNano": str(start_ns),
            "endTimeUnixNano": str(end_ns),
            "attributes": attributes,
        }

    @staticmethod
    def _span_id(request_id: str, label: str) -> str:
        digest = hashlib.sha256(f"{request_id}:{label}".encode()).hexdigest()
        return digest[:16]

    @staticmethod
    def _timestamp_ns(value: datetime) -> int:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.timestamp() * 1_000_000_000)

    @staticmethod
    def _request_window(events: list[TraceEvent]) -> tuple[int, int]:
        timestamps = [GuildTraceExporter._timestamp_ns(event.timestamp) for event in events]
        if not timestamps:
            now = GuildTraceExporter._timestamp_ns(datetime.now(timezone.utc))
            return now, now
        return min(timestamps), max(timestamps)


class NullGuildTraceExporter(GuildTraceExporter):
    def __init__(self) -> None:
        super().__init__(
            otlp_endpoint="",
            api_key=None,
            workspace_id=None,
            trace_view_url_template="https://app.guild.ai/?trace={request_id}",
        )

    @property
    def enabled(self) -> bool:
        return False

    async def export(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None = None,
        target_tool: str | None = None,
        scene_snapshot: dict[str, Any] | None = None,
    ) -> GuildExportResult:
        return GuildExportResult(exported=False)


def create_guild_exporter(settings: Any) -> GuildTraceExporter:
    if not settings.guild_trace_enabled or not settings.guild_otlp_endpoint:
        return NullGuildTraceExporter()
    return GuildTraceExporter(
        otlp_endpoint=settings.guild_otlp_endpoint,
        api_key=settings.guild_api_key,
        workspace_id=settings.guild_workspace_id,
        trace_view_url_template=settings.guild_trace_view_url_template,
        service_name=settings.guild_service_name,
        timeout=settings.guild_export_timeout,
    )
