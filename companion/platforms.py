from __future__ import annotations

import os
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path


class LaunchError(RuntimeError):
    pass


def open_url(url: str) -> None:
    webbrowser.open(url)


def launch_blender() -> None:
    system = platform.system()
    if system == "Darwin":
        _run(["open", "-a", "Blender"])
    elif system == "Windows":
        executable = shutil.which("blender") or _windows_app("Blender Foundation", "Blender", "blender.exe")
        _run([executable])
    else:
        _run([shutil.which("blender") or "blender"])


def launch_openscad(scad_path: Path) -> None:
    system = platform.system()
    if system == "Darwin":
        _run(["open", "-a", "OpenSCAD", str(scad_path)])
    elif system == "Windows":
        executable = shutil.which("openscad") or _windows_app("OpenSCAD", "openscad.exe")
        _run([executable, str(scad_path)])
    else:
        _run([shutil.which("openscad") or "openscad", str(scad_path)])


def _run(command: list[str]) -> None:
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise LaunchError(f"Could not launch {' '.join(command)}: {exc}") from exc


def _windows_app(*parts: str) -> str:
    roots = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")),
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")),
    ]
    for root in roots:
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return str(candidate)
    return str(roots[0].joinpath(*parts))
