from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.airbyte_exporter import AirbyteContextExporter
from backend.clickhouse_exporter import ClickHouseTraceExporter
from backend.composio_exporter import ComposioActionExporter
from backend.guild_exporter import GuildTraceExporter
from backend.openui_exporter import OpenUIExporter
from backend.sponsor_insights import scene_snapshot
from shared.contracts import TraceEvent
from shared.ir import EngineeringIR


@dataclass(frozen=True)
class SponsorExportBundle:
    guild_trace_url: str | None = None
    openui_lang: str | None = None
    openui_elements: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    scene_headline: str | None = None
    clickhouse_exported: bool = False
    composio_status: str | None = None
    airbyte_context_exported: bool = False


async def export_sponsors(
    *,
    guild_exporter: GuildTraceExporter,
    clickhouse_exporter: ClickHouseTraceExporter,
    composio_exporter: ComposioActionExporter,
    openui_exporter: OpenUIExporter,
    airbyte_exporter: AirbyteContextExporter,
    request_id: str,
    events: list[TraceEvent],
    prompt: str | None = None,
    target_tool: str | None = None,
    ir: EngineeringIR | None = None,
    notify_composio: bool = False,
    execution_status: str = "ok",
    airbyte_event_type: str = "prompt_completed",
) -> SponsorExportBundle:
    snapshot = scene_snapshot(prompt=prompt, ir=ir, target_tool=target_tool)
    openui_lang = openui_exporter.build_lang(
        request_id=request_id,
        prompt=prompt,
        trace=events,
        ir=ir,
    )
    openui_elements = tuple(
        openui_exporter.build_elements(
            request_id=request_id,
            prompt=prompt,
            trace=events,
            ir=ir,
        )
    )

    guild_result = await guild_exporter.export(
        request_id,
        events,
        prompt=prompt,
        target_tool=target_tool,
        scene_snapshot=snapshot,
    )
    clickhouse_result = await clickhouse_exporter.export(
        request_id,
        events,
        prompt=prompt,
        target_tool=target_tool,
        scene_snapshot=snapshot,
    )
    airbyte_result = await airbyte_exporter.export(
        request_id=request_id,
        event_type=airbyte_event_type,
        prompt=prompt,
        target_tool=target_tool,
        ir=ir,
        trace=events,
        execution_status=execution_status if notify_composio else None,
    )

    composio_status = None
    if notify_composio:
        composio_result = await composio_exporter.notify(
            request_id,
            events,
            prompt=prompt,
            execution_status=execution_status,
            ir=ir,
            target_tool=target_tool,
        )
        if composio_result.executed:
            composio_status = composio_result.status or "completed"
        elif composio_result.error:
            composio_status = f"error: {composio_result.error}"

    return SponsorExportBundle(
        guild_trace_url=guild_result.trace_view_url,
        openui_lang=openui_lang,
        openui_elements=openui_elements,
        scene_headline=snapshot.get("headline"),
        clickhouse_exported=clickhouse_result.exported,
        composio_status=composio_status,
        airbyte_context_exported=airbyte_result.exported,
    )
