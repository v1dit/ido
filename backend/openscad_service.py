from __future__ import annotations

import os
from pathlib import Path

from adapters.openscad.adapter import compile_ir_to_scad, export_with_openscad, write_scad
from backend.status import StatusStore
from shared.contracts import OpenScadExecution
from shared.ir import EngineeringIR


class OpenScadService:
    def __init__(self, status_store: StatusStore) -> None:
        self.status_store = status_store
        self.output_dir = Path(
            os.getenv("IDO_OUTPUT_DIR", str(Path.home() / ".ido" / "projects" / "default"))
        )

    def render(
        self,
        validated: EngineeringIR,
        export_formats: list[str],
    ) -> OpenScadExecution:
        self.status_store.update(phase="rendering", message="Exporting OpenSCAD artifacts")
        source = compile_ir_to_scad(validated)
        scad_path = write_scad(source, self.output_dir)
        artifacts, export_errors = export_with_openscad(
            scad_path,
            list(export_formats),
        )
        self.status_store.update(
            phase="completed",
            message="OpenSCAD project updated",
            artifacts=artifacts,
        )
        return OpenScadExecution(
            scad_path=str(scad_path),
            scad_source=source,
            artifacts=artifacts,
            export_errors=export_errors,
        )
