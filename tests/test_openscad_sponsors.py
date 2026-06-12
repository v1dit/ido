from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from backend.clickhouse_exporter import ClickHouseExportResult, NullClickHouseTraceExporter
from backend.composio_exporter import ComposioExportResult, NullComposioActionExporter
from backend.main import create_app
from backend.providers.fallback import DeterministicProvider


class RecordingComposioExporter(NullComposioActionExporter):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, list]] = []
        self.notify = AsyncMock(side_effect=self._notify)

    async def _notify(
        self,
        request_id,
        events,
        *,
        prompt=None,
        execution_status="ok",
        ir=None,
        target_tool=None,
    ):
        self.calls.append((request_id, list(events)))
        return ComposioExportResult(executed=True, status="completed")

    @property
    def enabled(self) -> bool:
        return True


class RecordingClickHouseExporter(NullClickHouseTraceExporter):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, list]] = []
        self.export = AsyncMock(side_effect=self._export)

    async def _export(self, request_id, events, *, prompt=None, target_tool=None, scene_snapshot=None):
        self.calls.append((request_id, list(events)))
        return ClickHouseExportResult(exported=True, rows=len(events))

    @property
    def enabled(self) -> bool:
        return True


def test_openscad_prompt_runs_full_sponsor_harness(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("IDO_OUTPUT_DIR", str(tmp_path))
    composio_exporter = RecordingComposioExporter()
    clickhouse_exporter = RecordingClickHouseExporter()
    client = TestClient(
        create_app(
            provider=DeterministicProvider(),
            composio_exporter=composio_exporter,
            clickhouse_exporter=clickhouse_exporter,
        )
    )

    response = client.post(
        "/api/openscad/prompt",
        json={"prompt": "make a house", "current_ir": None, "export_formats": []},
    )

    payload = response.json()
    assert payload["status"] == "ok"
    assert "Stack(" in payload["openui_lang"]
    assert payload["clickhouse_exported"] is True
    assert payload["composio_status"] == "completed"
    assert payload["execution"]["scad_path"].endswith("ido_current.scad")
    assert [event["step"] for event in payload["trace"]] == [
        "parse",
        "parse",
        "validate",
        "validate",
        "route",
        "route",
        "execute",
        "execute",
    ]
    assert len(composio_exporter.calls) == 1
    assert composio_exporter.calls[0][1][-1].step == "execute"
    assert len(clickhouse_exporter.calls) == 1
