from shared.ir import Dimensions, EngineeringIR, PrimitiveObject, Scene

from backend.sponsor_insights import scene_categories, scene_headline, scene_snapshot


def _box(id: str, label: str) -> PrimitiveObject:
    return PrimitiveObject(
        id=id,
        label=label,
        shape="box",
        dimensions=Dimensions(width=1.0, depth=1.0, height=1.0),
    )


def _bedroom_ir() -> EngineeringIR:
    return EngineeringIR(
        intent="make a cozy bedroom",
        history=["make a cozy bedroom"],
        scene=Scene(
            objects=[
                _box("bed_1", "bed_frame"),
                _box("pillow_1", "pillow"),
            ]
        ),
    )


def test_scene_headline_includes_object_count() -> None:
    headline = scene_headline(prompt="make a cozy bedroom", ir=_bedroom_ir())
    assert headline == "make a cozy bedroom · 2 objects"


def test_scene_categories_detect_furniture() -> None:
    labels = ["bed_frame", "pillow", "room_wall"]
    assert "bed" in scene_categories(labels)
    assert "room" in scene_categories(labels)


def test_scene_snapshot_compact_summary() -> None:
    snapshot = scene_snapshot(
        prompt="make a cozy bedroom",
        ir=_bedroom_ir(),
        target_tool="blender",
    )
    assert snapshot["object_count"] == 2
    assert snapshot["target_tool"] == "blender"
    assert "bed" in snapshot["categories"]
