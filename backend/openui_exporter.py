from __future__ import annotations

from typing import Any

from backend.sponsor_insights import object_labels, scene_categories, scene_headline
from shared.contracts import TraceEvent
from shared.ir import EngineeringIR

STEP_ORDER = ("parse", "validate", "route", "execute")


def _summarize_trace(events: list[TraceEvent]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for step in STEP_ORDER:
        step_events = [event for event in events if event.step == step]
        if not step_events:
            continue
        terminal = next(
            (
                event
                for event in reversed(step_events)
                if event.status in {"completed", "failed"}
            ),
            None,
        )
        status = terminal.status if terminal else step_events[-1].status
        summaries.append(
            {
                "step": step,
                "status": status,
                "duration_ms": terminal.duration_ms if terminal else None,
            }
        )
    return summaries


class OpenUIExporter:
    """Build OpenUI Lang for CAD-Agent trace and IR summaries."""

    def build_lang(
        self,
        *,
        request_id: str,
        prompt: str | None,
        trace: list[TraceEvent],
        ir: EngineeringIR | None = None,
    ) -> str:
        headline = scene_headline(prompt=prompt, ir=ir)
        lines = [
            "Stack(",
            '  Heading("CAD-Agent Request")',
            f'  Text("Request ID: {request_id}")',
        ]
        if headline:
            escaped_headline = headline.replace('"', "'")
            lines.append(f'  Text("{escaped_headline}")')
        if prompt:
            escaped = prompt.replace('"', "'")
            lines.append(f'  Text("Prompt: {escaped}")')

        if ir is not None:
            labels = object_labels(ir)
            categories = scene_categories(labels)
            history = ", ".join(ir.history[-3:]) if ir.history else "none"
            lines.extend(
                [
                    "  Card(",
                    '    Heading("Engineering IR")',
                    f'    Text("Objects: {len(labels)}")',
                ]
            )
            if categories:
                lines.append(f'    Text("Scene: {", ".join(categories)}")')
            if labels:
                preview = ", ".join(labels[:8])
                if len(labels) > 8:
                    preview += f" (+{len(labels) - 8} more)"
                lines.append(f'    Text("Parts: {preview}")')
            lines.extend(
                [
                    f'    Text("Recent history: {history}")',
                    "  )",
                ]
            )

        lines.extend(["  Card(", '    Heading("Request Timeline")'])
        for item in _summarize_trace(trace):
            duration = item["duration_ms"]
            duration_text = f"{duration:.1f} ms" if duration is not None else "pending"
            lines.append(
                f'    Text("{item["step"]}: {item["status"]} ({duration_text})")'
            )
        lines.extend(["  )", ")"])
        return "\n".join(lines)

    def build_elements(
        self,
        *,
        request_id: str,
        prompt: str | None,
        trace: list[TraceEvent],
        ir: EngineeringIR | None = None,
    ) -> list[dict[str, Any]]:
        headline = scene_headline(prompt=prompt, ir=ir)
        elements: list[dict[str, Any]] = [
            {"type": "Heading", "props": {"text": "CAD-Agent Request"}},
            {"type": "Text", "props": {"text": f"Request ID: {request_id}"}},
        ]
        if headline:
            elements.append({"type": "Text", "props": {"text": headline, "emphasis": True}})
        if prompt:
            elements.append({"type": "Text", "props": {"text": f"Prompt: {prompt}"}})
        if ir is not None:
            labels = object_labels(ir)
            categories = scene_categories(labels)
            body: list[dict[str, Any]] = [
                {"type": "Text", "props": {"text": f"Objects: {len(labels)}"}},
            ]
            if categories:
                body.append(
                    {"type": "Text", "props": {"text": f"Scene: {', '.join(categories)}"}}
                )
            if labels:
                body.append(
                    {
                        "type": "Text",
                        "props": {"text": f"Parts: {', '.join(labels[:10])}"},
                    }
                )
            elements.append(
                {
                    "type": "Card",
                    "props": {"title": "Engineering IR", "body": body},
                }
            )
        timeline_rows = []
        for item in _summarize_trace(trace):
            duration = item["duration_ms"]
            duration_text = f"{duration:.1f} ms" if duration is not None else "pending"
            timeline_rows.append(
                {
                    "type": "Text",
                    "props": {
                        "text": f'{item["step"]}: {item["status"]} ({duration_text})',
                    },
                }
            )
        elements.append(
            {
                "type": "Card",
                "props": {"title": "Request Timeline", "body": timeline_rows},
            }
        )
        return elements
