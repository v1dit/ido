from __future__ import annotations

import os
from pathlib import Path

from backend.airbyte_exporter import AirbyteContextExporter
from backend.clickhouse_exporter import ClickHouseTraceExporter
from backend.composio_exporter import ComposioActionExporter
from backend.config import Settings
from backend.guild_exporter import GuildTraceExporter
from backend.providers.base import IRProvider
from shared.contracts import IntegrationsStatus


def build_integrations_status(
    *,
    settings: Settings,
    provider: IRProvider,
    guild_exporter: GuildTraceExporter,
    clickhouse_exporter: ClickHouseTraceExporter,
    composio_exporter: ComposioActionExporter,
    airbyte_exporter: AirbyteContextExporter,
    clickhouse_reachable: bool | None,
) -> IntegrationsStatus:
    capabilities: list[str] = [
        "OpenUI Lang on every prompt (local generator)",
    ]
    if guild_exporter.enabled:
        capabilities.append("Guild OTLP trace export with scene metadata")
    if clickhouse_exporter.enabled and clickhouse_reachable:
        capabilities.append("ClickHouse trace analytics with object labels")
    elif clickhouse_exporter.enabled:
        capabilities.append("ClickHouse configured (awaiting connection)")
    if composio_exporter.enabled:
        capabilities.append("Composio post-build notifications with scene summary")
    if airbyte_exporter.enabled:
        capabilities.append("Airbyte JSONL context layer for design history")
    if os.getenv("PIONEER_API_KEY"):
        capabilities.append("Pioneer inference via OpenAI-compatible API")
    if Path("render.yaml").is_file():
        capabilities.append("Render deploy blueprint (render.yaml)")
    if Path("deploy_truefoundry.py").is_file():
        capabilities.append("TrueFoundry deploy script + Dockerfile")

    return IntegrationsStatus(
        provider=provider.name,
        pioneer_configured=bool(os.getenv("PIONEER_API_KEY")),
        pioneer_model=settings.pioneer_model_id if settings.provider == "pioneer" else None,
        clickhouse_enabled=clickhouse_exporter.enabled,
        clickhouse_reachable=clickhouse_reachable,
        clickhouse_table=settings.clickhouse_table if clickhouse_exporter.enabled else None,
        guild_enabled=guild_exporter.enabled,
        openui_active=True,
        composio_enabled=composio_exporter.enabled,
        airbyte_enabled=airbyte_exporter.enabled,
        truefoundry_available=Path("deploy_truefoundry.py").is_file(),
        render_blueprint=Path("render.yaml").is_file(),
        capabilities=capabilities,
    )
