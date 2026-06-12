from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from companion.platforms import launch_blender, launch_openscad, open_url

API_URL = os.getenv("IDO_API_URL", "http://127.0.0.1:8010").rstrip("/")
STATE_DIR = Path(os.getenv("IDO_STATE_DIR", str(Path.home() / ".ido")))
PROJECT_DIR = Path(
    os.getenv("IDO_OUTPUT_DIR", str(STATE_DIR / "projects" / "default"))
)
IR_PATH = PROJECT_DIR / "ido_current.ir.json"
SCAD_PATH = PROJECT_DIR / "ido_current.scad"
LOG_PATH = STATE_DIR / "companion.log"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ido",
        description="Local AI companion for Blender and OpenSCAD.",
    )
    subcommands = parser.add_subparsers(dest="command")

    open_parser = subcommands.add_parser("open", help="Open a CAD tool")
    open_parser.add_argument("tool", choices=["blender", "openscad"])

    prompt_parser = subcommands.add_parser("prompt", help="Send a design prompt")
    prompt_parser.add_argument("--tool", required=True, choices=["blender", "openscad"])
    prompt_parser.add_argument("prompt", nargs="+")

    pet_parser = subcommands.add_parser("pet", help="Show or hide the desktop pet")
    pet_parser.add_argument("action", choices=["show", "hide"])

    subcommands.add_parser("status", help="Print companion status")
    subcommands.add_parser("serve", help="Run the local API in the foreground")
    subcommands.add_parser("reset", help="Start a fresh project (clears stored IR and outputs)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        from backend.__main__ import uvicorn

        uvicorn.run("backend.main:app", host="127.0.0.1", port=8010, reload=False)
        return 0
    if args.command == "reset":
        removed = _reset_project()
        print(f"Removed {', '.join(removed)}." if removed else "Project already clean.")
        return 0

    ensure_backend()
    if args.command is None:
        open_url(API_URL)
        return 0
    if args.command == "open":
        if args.tool == "blender":
            launch_blender()
        else:
            PROJECT_DIR.mkdir(parents=True, exist_ok=True)
            if not SCAD_PATH.exists():
                SCAD_PATH.write_text("// idō OpenSCAD project\n$fn = 64;\n", encoding="utf-8")
            launch_openscad(SCAD_PATH)
        return 0
    if args.command == "prompt":
        payload = prompt(args.tool, " ".join(args.prompt))
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("status") == "ok" else 1
    if args.command == "pet":
        visible = args.action == "show"
        _request("POST", "/api/pet/visibility", {"visible": visible})
        if visible:
            start_pet()
        return 0
    if args.command == "status":
        print(json.dumps(_request("GET", "/api/status"), indent=2))
        return 0
    return 2


def prompt(tool: str, text: str) -> dict[str, Any]:
    current_ir = _read_ir()
    if tool == "openscad":
        payload = _request(
            "POST",
            "/api/openscad/prompt",
            {"prompt": text, "current_ir": current_ir},
        )
    else:
        payload = _request(
            "POST",
            "/api/prompt",
            {"prompt": text, "current_ir": current_ir, "target_tool": "blender"},
        )
    if payload.get("status") == "ok" and payload.get("ir"):
        PROJECT_DIR.mkdir(parents=True, exist_ok=True)
        IR_PATH.write_text(json.dumps(payload["ir"], indent=2), encoding="utf-8")
    return payload


def ensure_backend(timeout: float = 12.0) -> None:
    if _healthy():
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, "-m", "backend"],
            stdout=log,
            stderr=log,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "IDO_OUTPUT_DIR": str(PROJECT_DIR)},
        )
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _healthy():
            return
        time.sleep(0.2)
    raise RuntimeError(f"idō backend did not start; see {LOG_PATH}")


def start_pet() -> None:
    try:
        subprocess.Popen(
            [sys.executable, "-m", "companion.pet"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(f"Could not start the idō pet: {exc}") from exc


def _healthy() -> bool:
    try:
        payload = _request("GET", "/api/health", timeout=0.5)
        return payload.get("status") == "healthy"
    except RuntimeError:
        return False


def _reset_project() -> list[str]:
    removed = []
    candidates = [IR_PATH, SCAD_PATH] + [
        PROJECT_DIR / f"ido_current.{ext}" for ext in ("stl", "png", "3mf", "svg")
    ]
    for path in candidates:
        if path.exists():
            path.unlink()
            removed.append(path.name)
    return removed


def _read_ir() -> dict[str, Any] | None:
    try:
        return json.loads(IR_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 120.0,
) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Companion request failed: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
