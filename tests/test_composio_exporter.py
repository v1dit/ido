import asyncio
from datetime import datetime, timezone

from backend.composio_exporter import ComposioActionExporter, create_composio_exporter
from backend.config import Settings
from shared.contracts import TraceEvent


def _event(step: str = "execute") -> TraceEvent:
    return TraceEvent(
        request_id="req1",
        step=step,  # type: ignore[arg-type]
        status="completed",
        timestamp=datetime(2026, 6, 10, tzinfo=timezone.utc),
        duration_ms=12.0,
    )


def test_composio_exporter_executes_configured_tool() -> None:
    calls: list[tuple[str, str, dict]] = []

    def fake_execute(tool_slug, user_id, arguments):
        calls.append((tool_slug, user_id, arguments))
        return {"status": "completed"}

    exporter = ComposioActionExporter(
        api_key="test-key",
        user_id="user_123",
        tool_slug="SLACK_SEND_MESSAGE",
        execute_callable=fake_execute,
    )

    result = asyncio.run(
        exporter.notify(
            "req1",
            [_event("parse"), _event("execute")],
            prompt="add more windows",
            execution_status="ok",
        )
    )

    assert result.executed is True
    assert result.status == "completed"
    assert calls[0][0] == "SLACK_SEND_MESSAGE"
    assert "add more windows" in calls[0][2]["summary"]
    assert calls[0][2]["object_count"] == 0


def test_create_composio_exporter_disabled_by_default() -> None:
    exporter = create_composio_exporter(Settings.from_env())
    assert exporter.enabled is False
