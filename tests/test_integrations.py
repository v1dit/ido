from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.clickhouse_exporter import ClickHouseExportResult, NullClickHouseTraceExporter
from backend.main import create_app
from backend.providers.base import IRGenerationError
from backend.providers.fallback import DeterministicProvider


class RecordingClickHouseExporter(NullClickHouseTraceExporter):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, list]] = []
        self.export = AsyncMock(side_effect=self._export)
        self.ping = AsyncMock(return_value=True)
        self.query_recent = AsyncMock(return_value=[])

    async def _export(self, request_id, events, *, prompt=None, target_tool=None, scene_snapshot=None):
        self.calls.append((request_id, list(events)))
        new_count = len(events) - (len(self.calls) > 1 and len(self.calls[-2][1]) or 0)
        return ClickHouseExportResult(exported=True, rows=max(new_count, len(events)))

    @property
    def enabled(self) -> bool:
        return True


class FailingPioneer:
    name = "pioneer"

    async def generate(self, _prompt, _current_ir):
        raise IRGenerationError("pioneer unavailable")


def test_integrations_endpoint_reports_pioneer_and_clickhouse(monkeypatch) -> None:
    monkeypatch.setenv("PIONEER_API_KEY", "test-key")
    monkeypatch.setenv("CAD_AGENT_PROVIDER", "pioneer")
    clickhouse = RecordingClickHouseExporter()
    client = TestClient(
        create_app(
            provider=DeterministicProvider(),
            clickhouse_exporter=clickhouse,
        )
    )

    payload = client.get("/api/integrations").json()

    assert payload["pioneer_configured"] is True
    assert payload["clickhouse_enabled"] is True
    assert payload["clickhouse_reachable"] is True
    assert payload["openui_active"] is True
    assert any("OpenUI Lang" in item for item in payload["capabilities"])


def test_execution_export_uses_saved_request_context() -> None:
    clickhouse = RecordingClickHouseExporter()
    client = TestClient(
        create_app(
            provider=DeterministicProvider(),
            clickhouse_exporter=clickhouse,
        )
    )

    generated = client.post(
        "/api/prompt",
        json={
            "prompt": "make a house",
            "current_ir": None,
            "target_tool": "blender",
        },
    ).json()
    request_id = generated["request_id"]

    client.post(
        "/api/execution",
        json={
            "request_id": request_id,
            "target_tool": "blender",
            "status": "ok",
            "duration_ms": 9.0,
        },
    )

    assert len(clickhouse.calls) == 2
    assert clickhouse.calls[1][1][-1].step == "execute"
    status = client.get("/api/status").json()
    assert status["clickhouse_exported"] is True
    assert status["provider"] == "deterministic"


def test_resilient_provider_records_inference_provider() -> None:
    from backend.providers.factory import NamedResilientProvider

    provider = NamedResilientProvider(
        "pioneer+deterministic",
        FailingPioneer(),
        DeterministicProvider(),
    )
    client = TestClient(create_app(provider=provider))

    response = client.post(
        "/api/prompt",
        json={
            "prompt": "make a house",
            "current_ir": None,
            "target_tool": "blender",
        },
    ).json()

    parse_event = next(
        event
        for event in response["trace"]
        if event["step"] == "parse" and event["status"] == "completed"
    )
    assert parse_event["metadata"]["inference_provider"] == "deterministic"
    assert client.get("/api/status").json()["inference_provider"] == "deterministic"
