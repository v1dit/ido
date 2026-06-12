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
    prompt = os.getenv("CAD_AGENT_PROMPT", "make a house")
    follow_up = os.getenv("CAD_AGENT_FOLLOW_UP")
    output_path = Path(
        os.getenv("CAD_AGENT_BLEND_OUTPUT", ROOT / "blender-render.blend")
    ).resolve()
    client = BackendClient(backend_url)
    ido_blender.register()

    _, first_execution, first_count = prompt_execute_and_report(
        client, bpy.context, prompt, None
    )

    second_count = first_count
    second_execution = None
    if follow_up:
        _, second_execution, second_count = prompt_execute_and_report(
            client, bpy.context, follow_up, load_ir(bpy.context.scene)
        )

    assert first_execution is not None
    assert first_execution["event"]["step"] == "execute"
    if follow_up:
        assert second_execution is not None

    bpy.ops.wm.save_as_mainfile(filepath=str(output_path))
    print(f"IDO_RENDER_OK objects={second_count} blend={output_path}")


if __name__ == "__main__":
    main()
