from __future__ import annotations

import os
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "adapters" / "blender"))

import ido_blender  # noqa: E402
from ido_blender.client import BackendClient  # noqa: E402
from ido_blender.harness import prompt_execute_and_report  # noqa: E402
from ido_blender.state import load_ir  # noqa: E402


def main() -> None:
    backend_url = os.getenv("CAD_AGENT_BACKEND_URL", "http://127.0.0.1:8010")
    output_path = Path(
        os.getenv("CAD_AGENT_BLEND_OUTPUT", ROOT / "blender-smoke-test.blend")
    ).resolve()
    client = BackendClient(backend_url)
    ido_blender.register()

    first, first_execution, first_count = prompt_execute_and_report(
        client, bpy.context, "make a house", None
    )
    body_pointer = bpy.data.objects["CAD_main_body"].as_pointer()

    second, second_execution, second_count = prompt_execute_and_report(
        client, bpy.context, "add more windows", load_ir(bpy.context.scene)
    )

    assert first["status"] == "ok", first
    assert second["status"] == "ok", second
    assert first_count == 5
    assert second_count == 9
    assert bpy.data.objects["CAD_main_body"].as_pointer() == body_pointer
    assert load_ir(bpy.context.scene)["history"] == [
        "make a house",
        "add more windows",
    ]
    assert first_execution is not None
    assert second_execution is not None
    assert first_execution["event"]["step"] == "execute"
    assert second_execution["event"]["step"] == "execute"

    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    bpy.ops.wm.open_mainfile(filepath=str(output_path))
    assert load_ir(bpy.context.scene)["history"][-1] == "add more windows"
    print(f"CAD_AGENT_SMOKE_OK first={first_count} second={second_count}")


if __name__ == "__main__":
    main()
