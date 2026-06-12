from __future__ import annotations

import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from companion.cli import API_URL, ensure_backend

try:
    from PySide6.QtCore import QPoint, Qt, QTimer, Signal
    from PySide6.QtSvgWidgets import QSvgWidget
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover - depends on desktop extra
    raise SystemExit("Install the desktop extra: pip install 'cad-agent[desktop]'") from exc


class PetWindow(QWidget):
    prompt_finished = Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._drag_origin = QPoint()
        self.setWindowTitle("idō pet")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(360)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(14, 14, 14, 14)
        shell.setSpacing(8)

        pet = QSvgWidget(str(Path(__file__).with_name("assets") / "ido_pet.svg"))
        pet.setFixedSize(132, 108)
        shell.addWidget(pet, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.status_label = QLabel("idō is ready")
        self.status_label.setWordWrap(True)
        self.status_label.setObjectName("status")
        shell.addWidget(self.status_label)

        controls = QHBoxLayout()
        self.tool = QComboBox()
        self.tool.addItems(["blender", "openscad"])
        controls.addWidget(self.tool)
        self.prompt_input = QLineEdit()
        self.prompt_input.setPlaceholderText("Describe what to build")
        self.prompt_input.returnPressed.connect(self.submit_prompt)
        controls.addWidget(self.prompt_input, stretch=1)
        shell.addLayout(controls)

        actions = QHBoxLayout()
        submit = QPushButton("Prompt")
        submit.clicked.connect(self.submit_prompt)
        actions.addWidget(submit)
        blender = QPushButton("Open Blender")
        blender.clicked.connect(lambda: self._run_cli(["open", "blender"]))
        actions.addWidget(blender)
        openscad = QPushButton("Open OpenSCAD")
        openscad.clicked.connect(lambda: self._run_cli(["open", "openscad"]))
        actions.addWidget(openscad)
        shell.addLayout(actions)

        self.setStyleSheet(
            """
            QWidget { color: #f4f4f4; font: 13px "Inter", "Arial"; }
            PetWindow { background: transparent; }
            QLabel#status { background: #0b0b0b; border: 1px solid #484848;
              border-radius: 12px; padding: 12px; font-weight: 600; }
            QLineEdit, QComboBox { background: #111; border: 1px solid #484848;
              border-radius: 7px; padding: 8px; }
            QPushButton { background: #f4f4f4; color: #090909; border: 0;
              border-radius: 7px; padding: 8px 10px; font-weight: 700; }
            QPushButton:hover { background: #d8d8d8; }
            """
        )

        self.prompt_finished.connect(self._handle_prompt_result)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(750)

    def submit_prompt(self) -> None:
        text = self.prompt_input.text().strip()
        if not text:
            return
        self.prompt_input.clear()
        self.status_label.setText(f"Working in {self.tool.currentText()}...")
        tool = self.tool.currentText()
        threading.Thread(
            target=self._send_prompt,
            args=(tool, text),
            daemon=True,
        ).start()

    def refresh_status(self) -> None:
        try:
            status = _request("GET", "/api/status")
        except RuntimeError:
            return
        if not status.get("pet_visible", True):
            self.hide()
            return
        self.show()
        self.status_label.setText(status.get("message", "idō is ready"))

    def mousePressEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_origin)

    def _send_prompt(self, tool: str, text: str) -> None:
        path = "/api/openscad/prompt" if tool == "openscad" else "/api/prompt"
        payload: dict[str, Any] = {"prompt": text, "current_ir": None}
        if tool == "blender":
            payload["target_tool"] = "blender"
        try:
            result = _request("POST", path, payload)
        except RuntimeError as exc:
            result = {"status": "error", "error": str(exc)}
        self.prompt_finished.emit(result)

    def _handle_prompt_result(self, payload: dict[str, Any]) -> None:
        if payload.get("status") == "ok":
            self.status_label.setText("Done. Your model is ready.")
        else:
            self.status_label.setText(payload.get("error", "The request failed."))

    def _run_cli(self, arguments: list[str]) -> None:
        from companion.cli import main

        threading.Thread(target=main, args=(arguments,), daemon=True).start()


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"{API_URL}{path}",
        data=body,
        method=method,
        headers={"content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError) as exc:
        raise RuntimeError(str(exc)) from exc


def main() -> int:
    ensure_backend()
    app = QApplication(sys.argv)
    window = PetWindow()
    window.show()
    screen = app.primaryScreen().availableGeometry()
    window.move(screen.right() - window.width() - 24, screen.bottom() - window.height() - 24)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
