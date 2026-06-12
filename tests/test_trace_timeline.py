from adapters.blender.ido_blender.trace_timeline import format_trace_timeline, summarize_trace


def test_summarize_trace_orders_steps_with_durations() -> None:
    trace = [
        {"step": "parse", "status": "started"},
        {"step": "parse", "status": "completed", "duration_ms": 10.0},
        {"step": "validate", "status": "started"},
        {"step": "validate", "status": "completed", "duration_ms": 4.5},
        {"step": "route", "status": "started"},
        {"step": "route", "status": "completed", "duration_ms": 1.0},
        {"step": "execute", "status": "completed", "duration_ms": 25.0},
    ]

    summary = summarize_trace(trace)

    assert [item["step"] for item in summary] == [
        "parse",
        "validate",
        "route",
        "execute",
    ]
    assert summary[0]["duration_ms"] == 10.0
    assert summary[-1]["duration_ms"] == 25.0


def test_format_trace_timeline_includes_request_id() -> None:
    rendered = format_trace_timeline(
        [{"step": "parse", "status": "completed", "duration_ms": 3.0}],
        request_id="abc123",
    )

    assert "Request ID: abc123" in rendered
    assert "parse" in rendered and "completed" in rendered and "3.0 ms" in rendered
