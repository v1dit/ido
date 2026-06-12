from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from backend.sponsor_insights import scene_headline, scene_snapshot
from shared.contracts import TraceEvent
from shared.ir import EngineeringIR

logger = logging.getLogger("cad_agent.composio")

STEP_ORDER = ("parse", "validate", "route", "execute")


@dataclass(frozen=True)
class ComposioExportResult:
    executed: bool
    status: str | None = None
    error: str | None = None


def _trace_summary(request_id: str, prompt: str | None, events: list[TraceEvent]) -> str:
    lines = [f"CAD-Agent request {request_id}"]
    if prompt:
        lines.append(f"Prompt: {prompt}")
    for step in STEP_ORDER:
        step_events = [event for event in events if event.step == step]
        if not step_events:
            continue
        terminal = next(
            (
                event
                for event in reversed(step_events)
                if event.status in {"completed", "failed"}
            ),
            None,
        )
        if terminal is None:
            continue
        duration = terminal.duration_ms
        duration_text = f"{duration:.1f} ms" if duration is not None else "n/a"
        lines.append(f"{step}: {terminal.status} ({duration_text})")
    return "\n".join(lines)


class ComposioActionExporter:
    def __init__(
        self,
        *,
        api_key: str,
        user_id: str,
        tool_slug: str,
        execute_callable: Callable[[str, str, dict[str, Any]], dict[str, Any]] | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._user_id = user_id
        self._tool_slug = tool_slug
        self._execute_callable = execute_callable
        self._timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self._api_key and self._tool_slug and self._user_id)

    async def notify(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None = None,
        execution_status: str = "ok",
        ir: EngineeringIR | None = None,
        target_tool: str | None = None,
    ) -> ComposioExportResult:
        if not self.enabled or not events:
            return ComposioExportResult(executed=False)

        snapshot = scene_snapshot(prompt=prompt, ir=ir, target_tool=target_tool)
        headline = scene_headline(prompt=prompt, ir=ir)
        arguments = {
            "request_id": request_id,
            "prompt": prompt or "",
            "execution_status": execution_status,
            "summary": _trace_summary(request_id, prompt, events),
            "scene_headline": headline or "",
            "object_count": snapshot["object_count"],
            "object_labels": snapshot["object_labels"],
            "scene_categories": snapshot["categories"],
        }
        try:
            result = await asyncio.to_thread(
                self._execute_tool,
                self._tool_slug,
                self._user_id,
                arguments,
            )
        except Exception as exc:  # noqa: BLE001 - surface partner SDK failures
            logger.warning("composio action failed for %s: %s", request_id, exc)
            return ComposioExportResult(executed=False, error=str(exc))

        status = "completed"
        if isinstance(result, dict):
            status = str(result.get("status") or result.get("successful") or "completed")
        logger.info("composio action executed request_id=%s tool=%s", request_id, self._tool_slug)
        return ComposioExportResult(executed=True, status=status)

    def _execute_tool(
        self,
        tool_slug: str,
        user_id: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        if self._execute_callable is not None:
            return self._execute_callable(tool_slug, user_id, arguments)

        from composio import Composio

        composio = Composio(api_key=self._api_key)
        result = composio.tools.execute(
            tool_slug,
            arguments,
            user_id=user_id,
        )
        if isinstance(result, dict):
            return result
        return {"status": "completed", "result": json.dumps(result, default=str)}


class NullComposioActionExporter(ComposioActionExporter):
    def __init__(self) -> None:
        super().__init__(api_key="", user_id="", tool_slug="")

    @property
    def enabled(self) -> bool:
        return False

    async def notify(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None = None,
        execution_status: str = "ok",
        ir: EngineeringIR | None = None,
        target_tool: str | None = None,
    ) -> ComposioExportResult:
        return ComposioExportResult(executed=False)


def create_composio_exporter(settings: Any) -> ComposioActionExporter:
    if not settings.composio_enabled or not settings.composio_api_key:
        return NullComposioActionExporter()
    return ComposioActionExporter(
        api_key=settings.composio_api_key,
        user_id=settings.composio_user_id,
        tool_slug=settings.composio_tool_slug,
        timeout=settings.composio_export_timeout,
    )
