from __future__ import annotations

from typing import Any

from shared.contracts import TraceEvent
from shared.ir import EngineeringIR

FURNITURE_KEYWORDS = {
    "bed": ("bed", "mattress", "pillow", "headboard"),
    "chair": ("chair", "seat"),
    "desk": ("desk",),
    "room": ("room_", "wall_", "floor", "rug"),
    "house": ("house", "roof", "door", "window"),
}


def object_labels(ir: EngineeringIR | None) -> list[str]:
    if ir is None:
        return []
    return [item.label for item in ir.scene.objects]


def scene_categories(labels: list[str]) -> list[str]:
    joined = " ".join(labels).lower()
    found: list[str] = []
    for category, keywords in FURNITURE_KEYWORDS.items():
        if any(keyword in joined for keyword in keywords):
            found.append(category)
    return found


def scene_headline(*, prompt: str | None, ir: EngineeringIR | None) -> str | None:
    labels = object_labels(ir)
    if not labels and not prompt:
        return None
    categories = scene_categories(labels)
    count = len(labels)
    if prompt:
        base = prompt.strip().rstrip(".")
    elif categories:
        base = f"{categories[0]} scene"
    else:
        base = "CAD scene"
    if count:
        return f"{base} · {count} objects"
    return base


def scene_snapshot(
    *,
    prompt: str | None,
    ir: EngineeringIR | None,
    target_tool: str | None = None,
) -> dict[str, Any]:
    labels = object_labels(ir)
    categories = scene_categories(labels)
    return {
        "headline": scene_headline(prompt=prompt, ir=ir),
        "object_count": len(labels),
        "object_labels": labels[:24],
        "categories": categories,
        "target_tool": target_tool,
        "intent": ir.intent if ir is not None else prompt,
    }


def trace_duration_ms(events: list[TraceEvent]) -> float | None:
    total = 0.0
    found = False
    for event in events:
        if event.duration_ms is not None and event.status in {"completed", "failed"}:
            total += event.duration_ms
            found = True
    return round(total, 3) if found else None
