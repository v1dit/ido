from __future__ import annotations

from typing import Any

STEP_ORDER = ("parse", "validate", "route", "execute")


def summarize_trace(trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for step in STEP_ORDER:
        events = [event for event in trace if event.get("step") == step]
        if not events:
            continue
        terminal = next(
            (
                event
                for event in reversed(events)
                if event.get("status") in {"completed", "failed"}
            ),
            None,
        )
        status = terminal.get("status") if terminal else events[-1].get("status", "started")
        duration_ms = terminal.get("duration_ms") if terminal else None
        summaries.append(
            {
                "step": step,
                "status": status,
                "duration_ms": duration_ms,
            }
        )
    return summaries


def format_trace_timeline(trace: list[dict[str, Any]], *, request_id: str | None = None) -> str:
    lines = ["CAD-Agent Request Timeline", "=========================="]
    if request_id:
        lines.append(f"Request ID: {request_id}")
    lines.append("")

    for item in summarize_trace(trace):
        duration = item["duration_ms"]
        duration_text = f"{duration:.1f} ms" if duration is not None else "—"
        lines.append(f"{item['step']:<8} {item['status']:<10} {duration_text}")

    return "\n".join(lines)
