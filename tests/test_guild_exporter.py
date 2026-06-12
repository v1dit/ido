from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch

from backend.config import Settings
from backend.guild_exporter import GuildTraceExporter, create_guild_exporter
from shared.contracts import TraceEvent
from shared.ir import Dimensions, EngineeringIR, PrimitiveObject, Scene


def _event(
    *,
    request_id: str = "abc123",
    step: str = "parse",
    status: str = "completed",
    duration_ms: float | None = 12.5,
) -> TraceEvent:
    return TraceEvent(
        request_id=request_id,
        step=step,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        timestamp=datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc),
        duration_ms=duration_ms,
        metadata={"provider": "deterministic"},
    )


def test_guild_exporter_posts_otlp_payload() -> None:
    exporter = GuildTraceExporter(
        otlp_endpoint="https://guild.example/v1/traces",
        api_key="secret",
        workspace_id="workspace-1",
        trace_view_url_template="https://app.guild.ai/workspaces/{workspace_id}/sessions/{request_id}",
    )
    events = [
        _event(step="parse", status="started", duration_ms=None),
        _event(step="parse", status="completed", duration_ms=10.0),
        _event(step="validate", status="started", duration_ms=None),
        _event(step="validate", status="completed", duration_ms=5.0),
    ]

    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=10.0):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        response = BytesIO(b"{}")
        response.status = 200  # type: ignore[attr-defined]
        return response

    async def run_export():
        with patch("backend.guild_exporter.urlopen", side_effect=fake_urlopen):
            return await exporter.export(
                "abc123",
                events,
                prompt="make a house",
                target_tool="blender",
            )

    result = asyncio.run(run_export())

    assert result.exported is True
    assert (
        result.trace_view_url
        == "https://app.guild.ai/workspaces/workspace-1/sessions/abc123"
    )
    payload = captured["payload"]
    assert isinstance(payload, dict)
    spans = payload["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert spans[0]["name"] == "cad_agent.request"
    assert any(span["name"] == "cad_agent.parse" for span in spans)
    assert captured["headers"]["Authorization"] == "Bearer secret"


def test_guild_exporter_includes_scene_metadata() -> None:
    exporter = GuildTraceExporter(
        otlp_endpoint="https://guild.example/v1/traces",
        api_key=None,
        workspace_id=None,
        trace_view_url_template="https://app.guild.ai/?trace={request_id}",
    )
    ir = EngineeringIR(
        intent="make a desk",
        history=["make a desk"],
        scene=Scene(
            objects=[
                PrimitiveObject(
                    id="desk_top",
                    label="desk_top",
                    shape="box",
                    dimensions=Dimensions(width=1.2, depth=0.6, height=0.05),
                )
            ]
        ),
    )
    from backend.sponsor_insights import scene_snapshot

    payload = exporter._build_otlp_payload(
        "abc123",
        [_event(step="parse", status="completed")],
        prompt="make a desk",
        target_tool="blender",
        scene_snapshot=scene_snapshot(prompt="make a desk", ir=ir, target_tool="blender"),
    )
    attributes = payload["resourceSpans"][0]["resource"]["attributes"]
    keys = {item["key"] for item in attributes}
    assert "cad_agent.object_count" in keys
    assert "cad_agent.scene_headline" in keys
    assert "cad_agent.object_labels" in keys


def test_create_guild_exporter_disabled_by_default() -> None:
    settings = Settings.from_env()
    exporter = create_guild_exporter(settings)
    assert exporter.enabled is False
