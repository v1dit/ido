from datetime import datetime, timezone

from backend.openui_exporter import OpenUIExporter
from shared.contracts import TraceEvent
from shared.ir import Dimensions, EngineeringIR, PrimitiveObject, Scene


def _event(step: str, status: str, duration_ms: float | None = 10.0) -> TraceEvent:
    return TraceEvent(
        request_id="req1",
        step=step,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        timestamp=datetime(2026, 6, 10, tzinfo=timezone.utc),
        duration_ms=duration_ms,
    )


def test_openui_exporter_builds_lang_with_timeline() -> None:
    exporter = OpenUIExporter()
    lang = exporter.build_lang(
        request_id="req1",
        prompt="add more windows",
        trace=[
            _event("parse", "started", None),
            _event("parse", "completed", 10.0),
            _event("validate", "started", None),
            _event("validate", "completed", 4.0),
        ],
    )

    assert "Stack(" in lang
    assert "add more windows" in lang
    assert "parse: completed (10.0 ms)" in lang
    assert "validate: completed (4.0 ms)" in lang
    assert "add more windows ·" not in lang


def test_openui_exporter_includes_scene_labels_in_lang() -> None:
    exporter = OpenUIExporter()
    ir = EngineeringIR(
        intent="make a chair",
        history=["make a chair"],
        scene=Scene(
            objects=[
                PrimitiveObject(
                    id="c1",
                    label="chair_seat",
                    shape="box",
                    dimensions=Dimensions(width=1.0, depth=1.0, height=1.0),
                )
            ]
        ),
    )
    lang = exporter.build_lang(
        request_id="req1",
        prompt="make a chair",
        trace=[_event("parse", "completed", 3.0)],
        ir=ir,
    )
    assert "make a chair · 1 objects" in lang
    assert "chair_seat" in lang
    assert "Scene: chair" in lang


def test_openui_exporter_builds_elements() -> None:
    exporter = OpenUIExporter()
    elements = exporter.build_elements(
        request_id="req1",
        prompt="make a house",
        trace=[_event("parse", "completed", 3.0)],
    )

    assert elements[0]["type"] == "Heading"
    assert any(item["type"] == "Card" for item in elements)
