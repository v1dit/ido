import asyncio
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.airbyte_exporter import AirbyteContextExporter, create_airbyte_exporter
from backend.config import Settings
from shared.contracts import TraceEvent
from shared.ir import EngineeringIR, Scene


def _trace_event() -> TraceEvent:
    return TraceEvent(
        request_id="req1",
        step="parse",
        status="completed",
        timestamp=datetime(2026, 6, 10, tzinfo=timezone.utc),
        duration_ms=3.0,
    )


def _ir() -> EngineeringIR:
    return EngineeringIR(
        intent="make a house",
        history=["make a house"],
        scene=Scene(objects=[]),
    )


def test_airbyte_exporter_writes_jsonl(tmp_path: Path) -> None:
    exporter = AirbyteContextExporter(context_dir=str(tmp_path), endpoint=None)

    result = asyncio.run(
        exporter.export(
            request_id="req1",
            event_type="prompt_completed",
            prompt="make a house",
            target_tool="blender",
            ir=_ir(),
            trace=[_trace_event()],
        )
    )

    assert result.exported is True
    path = tmp_path / "cad_agent_context.jsonl"
    assert path.exists()
    record = json.loads(path.read_text(encoding="utf-8").strip())
    assert record["request_id"] == "req1"
    assert record["event_type"] == "prompt_completed"
    assert record["prompt"] == "make a house"
    assert record["ir"]["intent"] == "make a house"
    assert record["scene_summary"]["object_count"] == 0


def test_airbyte_exporter_posts_to_endpoint() -> None:
    exporter = AirbyteContextExporter(
        context_dir=None,
        endpoint="https://airbyte.example/context",
        api_key="secret",
    )
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=10.0):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        response = BytesIO(b"")
        response.status = 200  # type: ignore[attr-defined]
        return response

    async def run_export():
        with patch("backend.airbyte_exporter.urlopen", side_effect=fake_urlopen):
            return await exporter.export(
                request_id="req1",
                event_type="execution_completed",
                trace=[_trace_event()],
                execution_status="ok",
            )

    result = asyncio.run(run_export())
    assert result.exported is True
    assert captured["body"]["event_type"] == "execution_completed"


def test_create_airbyte_exporter_disabled_by_default() -> None:
    exporter = create_airbyte_exporter(Settings.from_env())
    assert exporter.enabled is False
