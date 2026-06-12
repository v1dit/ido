import asyncio
import json
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import patch

from backend.clickhouse_exporter import ClickHouseTraceExporter, create_clickhouse_exporter
from backend.config import Settings
from shared.contracts import TraceEvent


def _event() -> TraceEvent:
    return TraceEvent(
        request_id="req1",
        step="parse",
        status="completed",
        timestamp=datetime(2026, 6, 10, tzinfo=timezone.utc),
        duration_ms=8.5,
        metadata={"provider": "deterministic"},
    )


def test_clickhouse_exporter_inserts_json_rows() -> None:
    exporter = ClickHouseTraceExporter(
        host="clickhouse.example",
        port=8123,
        database="analytics",
        table="cad_agent_traces",
        username="default",
        password="secret",
    )
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout=10.0):
        captured["url"] = request.full_url
        captured["body"] = (
            request.data.decode("utf-8") if request.data is not None else ""
        )
        response = BytesIO(b"")
        response.status = 200  # type: ignore[attr-defined]
        return response

    async def run_export():
        with patch("backend.clickhouse_exporter.urlopen", side_effect=fake_urlopen):
            return await exporter.export(
                "req1",
                [_event()],
                prompt="make a house",
                target_tool="blender",
            )

    result = asyncio.run(run_export())

    assert result.exported is True
    assert result.rows == 1
    body = str(captured["body"])
    assert "req1" in body
    assert "make a house" in body
    assert "cad_agent_traces" in str(captured["url"])
    assert "JSONEachRow" in str(captured["url"])


def test_clickhouse_exporter_only_inserts_new_events() -> None:
    exporter = ClickHouseTraceExporter(
        host="clickhouse.example",
        port=8123,
        database="analytics",
        table="cad_agent_traces",
    )

    def fake_urlopen(request, timeout=10.0):
        response = BytesIO(b"")
        response.status = 200  # type: ignore[attr-defined]
        return response

    async def run_exports():
        with patch("backend.clickhouse_exporter.urlopen", side_effect=fake_urlopen):
            first = await exporter.export("req1", [_event()], prompt="make a house")
            second = await exporter.export(
                "req1",
                [_event(), _event()],
                prompt="make a house",
            )
            return first, second

    first, second = asyncio.run(run_exports())
    assert first.rows == 1
    assert second.rows == 1


def test_create_clickhouse_exporter_disabled_by_default() -> None:
    exporter = create_clickhouse_exporter(Settings.from_env())
    assert exporter.enabled is False
