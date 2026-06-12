import asyncio

import pytest
from fastapi.testclient import TestClient

from adapters.openscad.adapter import compile_ir_to_scad, validate_scad_source
from backend.main import create_app
from backend.providers.fallback import DeterministicProvider
from shared.validation import parse_and_validate_ir


def run(coroutine):
    return asyncio.run(coroutine)


@pytest.mark.parametrize(
    ("prompt", "min_objects", "required_labels"),
    [
        ("make a bed", 5, {"bed_mattress", "bed_headboard", "bed_pillow"}),
        ("make a chair", 6, {"chair_seat", "chair_back", "chair_leg_fl"}),
        ("make a desk", 5, {"desk_top", "desk_leg_fl"}),
        (
            "make a cozy bedroom",
            18,
            {"bed_mattress", "desk_top", "chair_seat", "rug", "room_floor"},
        ),
        (
            "make a home office",
            14,
            {"desk_top", "chair_seat", "office_floor", "office_wall_front"},
        ),
    ],
)
def test_furniture_prompts_generate_valid_ir(
    prompt: str,
    min_objects: int,
    required_labels: set[str],
) -> None:
    ir = run(DeterministicProvider().generate(prompt, None))
    validated = parse_and_validate_ir(ir)
    labels = {item.label for item in validated.scene.objects}

    assert len(validated.scene.objects) >= min_objects
    assert required_labels <= labels

    source = compile_ir_to_scad(validated)
    assert validate_scad_source(source) == []
    assert f"module {next(iter(required_labels))}()" in source
    assert "ido_scene();" in source


def test_furniture_api_prompt_returns_ok() -> None:
    client = TestClient(create_app())
    for prompt in ("make a bed", "make a chair", "make a desk", "make a cozy bedroom"):
        response = client.post(
            "/api/prompt",
            json={"prompt": prompt, "current_ir": None, "target_tool": "blender"},
        )
        payload = response.json()
        assert response.status_code == 200, payload
        assert payload["status"] == "ok", payload
        assert len(payload["ir"]["scene"]["objects"]) >= 5
