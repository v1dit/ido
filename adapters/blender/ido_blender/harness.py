from __future__ import annotations

from time import perf_counter
from typing import Any

from .client import BackendClient
from .state import save_ir, save_trace


def prompt_execute_and_report(
    client: BackendClient,
    context: Any,
    prompt: str,
    current_ir: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None, int]:
    """Run prompt → execute IR → report execution so the full sponsor harness fires."""
    from .executor import execute_ir

    started = perf_counter()
    response = client.prompt(prompt, current_ir)
    request_id = response.get("request_id")
    duration_ms = (perf_counter() - started) * 1000

    if response.get("status") != "ok" or not response.get("ir"):
        error = (
            response.get("error")
            or "; ".join(response.get("validation_errors", []))
            or "Backend did not return a model"
        )
        execution = None
        if request_id:
            execution = client.report_execution(
                request_id=request_id,
                status="error",
                duration_ms=duration_ms,
                error=error,
            )
            _persist_sponsor_metadata(context.scene, response, execution)
        raise RuntimeError(error)

    count = execute_ir(context, response["ir"])
    save_ir(context.scene, response["ir"], request_id)
    duration_ms = (perf_counter() - started) * 1000
    execution = None
    if request_id:
        execution = client.report_execution(
            request_id=request_id,
            status="ok",
            duration_ms=duration_ms,
        )
    _persist_sponsor_metadata(context.scene, response, execution)
    return response, execution, count


def _persist_sponsor_metadata(
    scene: Any,
    response: dict[str, Any],
    execution: dict[str, Any] | None,
) -> None:
    metadata = {**response, **(execution or {})}
    trace = list(metadata.get("trace", []))
    save_trace(
        scene,
        trace,
        guild_trace_url=metadata.get("guild_trace_url"),
        openui_lang=metadata.get("openui_lang"),
        composio_status=metadata.get("composio_status"),
        clickhouse_exported=metadata.get("clickhouse_exported"),
        airbyte_context_exported=metadata.get("airbyte_context_exported"),
    )
