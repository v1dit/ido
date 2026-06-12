from __future__ import annotations

from copy import deepcopy

from backend.providers.base import IRGenerationError
from shared.ir import (
    Dimensions,
    EngineeringIR,
    Material,
    PrimitiveObject,
    Scene,
    Vector3,
)


class DeterministicProvider:
    name = "deterministic"

    async def generate(
        self,
        prompt: str,
        current_ir: EngineeringIR | None,
    ) -> EngineeringIR:
        normalized = " ".join(prompt.lower().split())
        if "house" in normalized and (
            current_ir is None or "new house" in normalized or "make" in normalized
        ):
            return _house_ir(prompt)
        if current_ir is not None and "window" in normalized and (
            "more" in normalized or "add" in normalized
        ):
            return _add_windows(current_ir, prompt)
        if _matches(normalized, ("bedroom", "cozy bedroom", "furnished bedroom")):
            return _bedroom_ir(prompt)
        if _matches(normalized, ("office", "home office", "study room")):
            return _office_ir(prompt)
        if "bed" in normalized and _is_new_object_prompt(normalized, current_ir):
            return _bed_ir(prompt)
        if "chair" in normalized and _is_new_object_prompt(normalized, current_ir):
            return _chair_ir(prompt)
        if "desk" in normalized and _is_new_object_prompt(normalized, current_ir):
            return _desk_ir(prompt)
        raise IRGenerationError(
            "Offline demo mode supports: make a house, add more windows, "
            "make a bedroom, make an office, make a bed, make a chair, make a desk."
        )


def _matches(normalized: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in normalized for phrase in phrases)


def _is_new_object_prompt(normalized: str, current_ir: EngineeringIR | None) -> bool:
    return current_ir is None or any(
        word in normalized for word in ("make", "build", "create", "design", "new")
    )


def _house_ir(prompt: str) -> EngineeringIR:
    objects = [
        _box(
            "house_body",
            "main_body",
            (8.0, 6.0, 4.0),
            (0.0, 0.0, 2.0),
            "#D9B38C",
        ),
        PrimitiveObject(
            id="house_roof",
            label="roof_prism",
            shape="prism",
            dimensions=Dimensions(width=8.8, depth=6.8, height=2.4),
            position=Vector3(x=0.0, y=0.0, z=5.2),
            material=Material(color="#8B3A3A", roughness=0.8),
        ),
        _box(
            "front_door",
            "front_door",
            (1.4, 0.18, 2.5),
            (0.0, -3.09, 1.25),
            "#5B3924",
        ),
        _box(
            "window_front_left",
            "window_front_left",
            (1.4, 0.16, 1.3),
            (-2.3, -3.1, 2.3),
            "#72B7D2",
            roughness=0.2,
        ),
        _box(
            "window_front_right",
            "window_front_right",
            (1.4, 0.16, 1.3),
            (2.3, -3.1, 2.3),
            "#72B7D2",
            roughness=0.2,
        ),
    ]
    return EngineeringIR(intent=prompt, history=[prompt], scene=Scene(objects=objects))


def _bed_ir(prompt: str) -> EngineeringIR:
    objects = [
        _box("bed_mattress", "bed_mattress", (2.0, 1.6, 0.35), (0.0, 0.0, 0.175), "#E8E0D4"),
        _box("bed_headboard", "bed_headboard", (2.0, 0.1, 1.0), (0.0, -0.85, 0.5), "#5B3924"),
        _box("bed_frame_left", "bed_frame_left", (0.08, 1.6, 0.25), (-0.96, 0.0, 0.125), "#6B4423"),
        _box("bed_frame_right", "bed_frame_right", (0.08, 1.6, 0.25), (0.96, 0.0, 0.125), "#6B4423"),
        _box("bed_pillow", "bed_pillow", (0.6, 0.4, 0.12), (-0.55, -0.55, 0.41), "#F5F5F5"),
    ]
    return EngineeringIR(intent=prompt, history=[prompt], scene=Scene(objects=objects))


def _chair_ir(prompt: str) -> EngineeringIR:
    seat_z = 0.45
    objects = [
        _box("chair_seat", "chair_seat", (0.48, 0.48, 0.07), (0.0, 0.0, seat_z), "#333333"),
        _box("chair_back", "chair_back", (0.48, 0.06, 0.55), (0.0, -0.21, seat_z + 0.28), "#333333"),
        _box("chair_leg_fl", "chair_leg_fl", (0.05, 0.05, seat_z), (-0.2, 0.2, seat_z / 2), "#222222"),
        _box("chair_leg_fr", "chair_leg_fr", (0.05, 0.05, seat_z), (0.2, 0.2, seat_z / 2), "#222222"),
        _box("chair_leg_bl", "chair_leg_bl", (0.05, 0.05, seat_z), (-0.2, -0.2, seat_z / 2), "#222222"),
        _box("chair_leg_br", "chair_leg_br", (0.05, 0.05, seat_z), (0.2, -0.2, seat_z / 2), "#222222"),
    ]
    return EngineeringIR(intent=prompt, history=[prompt], scene=Scene(objects=objects))


def _desk_ir(prompt: str) -> EngineeringIR:
    top_z = 0.74
    objects = [
        _box("desk_top", "desk_top", (1.4, 0.72, 0.04), (0.0, 0.0, top_z), "#8B6914", roughness=0.45),
        _box("desk_leg_fl", "desk_leg_fl", (0.06, 0.06, top_z), (-0.64, 0.3, top_z / 2), "#5B3924"),
        _box("desk_leg_fr", "desk_leg_fr", (0.06, 0.06, top_z), (0.64, 0.3, top_z / 2), "#5B3924"),
        _box("desk_leg_bl", "desk_leg_bl", (0.06, 0.06, top_z), (-0.64, -0.3, top_z / 2), "#5B3924"),
        _box("desk_leg_br", "desk_leg_br", (0.06, 0.06, top_z), (0.64, -0.3, top_z / 2), "#5B3924"),
    ]
    return EngineeringIR(intent=prompt, history=[prompt], scene=Scene(objects=objects))


def _room_shell(prefix: str, width: float, depth: float, height: float) -> list[PrimitiveObject]:
    floor_t = 0.1
    wall_t = 0.12
    hw, hd = width / 2, depth / 2
    wall_z = height / 2 + floor_t
    return [
        _box(f"{prefix}_floor", f"{prefix}_floor", (width, depth, floor_t), (0.0, 0.0, floor_t / 2), "#C4A882"),
        _box(f"{prefix}_wall_front", f"{prefix}_wall_front", (width, wall_t, height), (0.0, -hd, wall_z), "#E8E4DC"),
        _box(f"{prefix}_wall_back", f"{prefix}_wall_back", (width, wall_t, height), (0.0, hd, wall_z), "#E8E4DC"),
        _box(f"{prefix}_wall_left", f"{prefix}_wall_left", (wall_t, depth, height), (-hw, 0.0, wall_z), "#E8E4DC"),
        _box(f"{prefix}_wall_right", f"{prefix}_wall_right", (wall_t, depth, height), (hw, 0.0, wall_z), "#E8E4DC"),
    ]


def _bedroom_ir(prompt: str) -> EngineeringIR:
    objects = _room_shell("room", 5.0, 4.5, 2.6)
    objects.extend(
        [
            _box("bed_mattress", "bed_mattress", (2.0, 1.6, 0.35), (-0.8, 0.6, 0.275), "#E8E0D4"),
            _box("bed_headboard", "bed_headboard", (2.0, 0.1, 1.0), (-0.8, -0.15, 0.6), "#5B3924"),
            _box("bed_pillow", "bed_pillow", (0.6, 0.4, 0.12), (-1.35, 0.05, 0.51), "#F5F5F5"),
            _box("nightstand", "nightstand", (0.45, 0.4, 0.55), (0.35, 0.55, 0.375), "#6B4423"),
            _box("desk_top", "desk_top", (1.2, 0.65, 0.04), (1.35, -1.2, 0.77), "#8B6914"),
            _box("desk_leg_fl", "desk_leg_fl", (0.05, 0.05, 0.75), (0.93, -0.95, 0.375), "#5B3924"),
            _box("desk_leg_fr", "desk_leg_fr", (0.05, 0.05, 0.75), (1.77, -0.95, 0.375), "#5B3924"),
            _box("desk_leg_bl", "desk_leg_bl", (0.05, 0.05, 0.75), (0.93, -1.45, 0.375), "#5B3924"),
            _box("desk_leg_br", "desk_leg_br", (0.05, 0.05, 0.75), (1.77, -1.45, 0.375), "#5B3924"),
            _box("chair_seat", "chair_seat", (0.45, 0.45, 0.07), (1.35, -0.55, 0.485), "#333333"),
            _box("chair_back", "chair_back", (0.45, 0.06, 0.5), (1.35, -0.76, 0.74), "#333333"),
            _box("chair_leg_fl", "chair_leg_fl", (0.05, 0.05, 0.45), (1.15, -0.35, 0.225), "#222222"),
            _box("chair_leg_fr", "chair_leg_fr", (0.05, 0.05, 0.45), (1.55, -0.35, 0.225), "#222222"),
            _box("chair_leg_bl", "chair_leg_bl", (0.05, 0.05, 0.45), (1.15, -0.75, 0.225), "#222222"),
            _box("chair_leg_br", "chair_leg_br", (0.05, 0.05, 0.45), (1.55, -0.75, 0.225), "#222222"),
            _box("rug", "rug", (2.2, 1.8, 0.02), (0.0, 0.0, 0.11), "#7A5C45", roughness=0.9),
        ]
    )
    return EngineeringIR(intent=prompt, history=[prompt], scene=Scene(objects=objects))


def _office_ir(prompt: str) -> EngineeringIR:
    objects = _room_shell("office", 4.5, 4.0, 2.6)
    top_z = 0.74
    seat_z = 0.45
    objects.extend(
        [
            _box("desk_top", "desk_top", (1.4, 0.72, 0.04), (0.0, -0.5, top_z), "#8B6914", roughness=0.45),
            _box("desk_leg_fl", "desk_leg_fl", (0.06, 0.06, top_z), (-0.64, -0.2, top_z / 2), "#5B3924"),
            _box("desk_leg_fr", "desk_leg_fr", (0.06, 0.06, top_z), (0.64, -0.2, top_z / 2), "#5B3924"),
            _box("desk_leg_bl", "desk_leg_bl", (0.06, 0.06, top_z), (-0.64, -0.8, top_z / 2), "#5B3924"),
            _box("desk_leg_br", "desk_leg_br", (0.06, 0.06, top_z), (0.64, -0.8, top_z / 2), "#5B3924"),
            _box("chair_seat", "chair_seat", (0.48, 0.48, 0.07), (0.0, 0.15, seat_z), "#333333"),
            _box("chair_back", "chair_back", (0.48, 0.06, 0.55), (0.0, -0.06, seat_z + 0.28), "#333333"),
            _box("chair_leg_fl", "chair_leg_fl", (0.05, 0.05, seat_z), (-0.2, 0.35, seat_z / 2), "#222222"),
            _box("chair_leg_fr", "chair_leg_fr", (0.05, 0.05, seat_z), (0.2, 0.35, seat_z / 2), "#222222"),
            _box("chair_leg_bl", "chair_leg_bl", (0.05, 0.05, seat_z), (-0.2, -0.05, seat_z / 2), "#222222"),
            _box("chair_leg_br", "chair_leg_br", (0.05, 0.05, seat_z), (0.2, -0.05, seat_z / 2), "#222222"),
        ]
    )
    return EngineeringIR(intent=prompt, history=[prompt], scene=Scene(objects=objects))


def _add_windows(current_ir: EngineeringIR, prompt: str) -> EngineeringIR:
    updated = deepcopy(current_ir)
    existing_ids = {item.id for item in updated.scene.objects}
    candidates = [
        _box(
            "window_left_front",
            "window_left_front",
            (0.16, 1.4, 1.3),
            (-4.1, -1.6, 2.3),
            "#72B7D2",
            roughness=0.2,
        ),
        _box(
            "window_left_back",
            "window_left_back",
            (0.16, 1.4, 1.3),
            (-4.1, 1.6, 2.3),
            "#72B7D2",
            roughness=0.2,
        ),
        _box(
            "window_right_front",
            "window_right_front",
            (0.16, 1.4, 1.3),
            (4.1, -1.6, 2.3),
            "#72B7D2",
            roughness=0.2,
        ),
        _box(
            "window_right_back",
            "window_right_back",
            (0.16, 1.4, 1.3),
            (4.1, 1.6, 2.3),
            "#72B7D2",
            roughness=0.2,
        ),
    ]
    updated.scene.objects.extend(
        candidate for candidate in candidates if candidate.id not in existing_ids
    )
    updated.intent = prompt
    updated.history.append(prompt)
    return updated


def _box(
    object_id: str,
    label: str,
    dimensions: tuple[float, float, float],
    position: tuple[float, float, float],
    color: str,
    *,
    roughness: float = 0.6,
) -> PrimitiveObject:
    width, depth, height = dimensions
    x, y, z = position
    return PrimitiveObject(
        id=object_id,
        label=label,
        shape="box",
        dimensions=Dimensions(width=width, depth=depth, height=height),
        position=Vector3(x=x, y=y, z=z),
        material=Material(color=color, roughness=roughness),
    )
