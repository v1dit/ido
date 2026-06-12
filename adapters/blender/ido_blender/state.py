from __future__ import annotations

import json
from typing import Any

IR_PROPERTY = "cad_agent_current_ir"
REQUEST_PROPERTY = "cad_agent_last_request_id"
TRACE_PROPERTY = "cad_agent_last_trace"
GUILD_TRACE_URL_PROPERTY = "cad_agent_guild_trace_url"
OPENUI_LANG_PROPERTY = "cad_agent_openui_lang"
COMPOSIO_STATUS_PROPERTY = "cad_agent_composio_status"
CLICKHOUSE_EXPORTED_PROPERTY = "cad_agent_clickhouse_exported"
AIRBYTE_EXPORTED_PROPERTY = "cad_agent_airbyte_exported"
COLLECTION_NAME = "CAD_AGENT"


def load_ir(scene: Any) -> dict[str, Any] | None:
    serialized = scene.get(IR_PROPERTY)
    if not serialized:
        return None
    try:
        value = json.loads(serialized)
    except (TypeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def save_ir(scene: Any, ir: dict[str, Any], request_id: str | None = None) -> None:
    scene[IR_PROPERTY] = json.dumps(ir, separators=(",", ":"), sort_keys=True)
    if request_id:
        scene[REQUEST_PROPERTY] = request_id


def save_trace(
    scene: Any,
    trace: list[dict[str, Any]],
    *,
    guild_trace_url: str | None = None,
    openui_lang: str | None = None,
    composio_status: str | None = None,
    clickhouse_exported: bool | None = None,
    airbyte_context_exported: bool | None = None,
) -> None:
    scene[TRACE_PROPERTY] = json.dumps(trace, separators=(",", ":"), sort_keys=True)
    if guild_trace_url:
        scene[GUILD_TRACE_URL_PROPERTY] = guild_trace_url
    else:
        scene.pop(GUILD_TRACE_URL_PROPERTY, None)
    if openui_lang:
        scene[OPENUI_LANG_PROPERTY] = openui_lang
    else:
        scene.pop(OPENUI_LANG_PROPERTY, None)
    if composio_status:
        scene[COMPOSIO_STATUS_PROPERTY] = composio_status
    else:
        scene.pop(COMPOSIO_STATUS_PROPERTY, None)
    if clickhouse_exported is not None:
        scene[CLICKHOUSE_EXPORTED_PROPERTY] = "true" if clickhouse_exported else "false"
    else:
        scene.pop(CLICKHOUSE_EXPORTED_PROPERTY, None)
    if airbyte_context_exported is not None:
        scene[AIRBYTE_EXPORTED_PROPERTY] = "true" if airbyte_context_exported else "false"
    else:
        scene.pop(AIRBYTE_EXPORTED_PROPERTY, None)


def load_trace(scene: Any) -> list[dict[str, Any]]:
    serialized = scene.get(TRACE_PROPERTY)
    if not serialized:
        return []
    try:
        value = json.loads(serialized)
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def load_guild_trace_url(scene: Any) -> str | None:
    value = scene.get(GUILD_TRACE_URL_PROPERTY)
    return value if isinstance(value, str) and value else None


def load_openui_lang(scene: Any) -> str | None:
    value = scene.get(OPENUI_LANG_PROPERTY)
    return value if isinstance(value, str) and value else None


def load_composio_status(scene: Any) -> str | None:
    value = scene.get(COMPOSIO_STATUS_PROPERTY)
    return value if isinstance(value, str) and value else None


def load_clickhouse_exported(scene: Any) -> bool:
    return scene.get(CLICKHOUSE_EXPORTED_PROPERTY) == "true"


def load_airbyte_context_exported(scene: Any) -> bool:
    return scene.get(AIRBYTE_EXPORTED_PROPERTY) == "true"


def clear_ir(scene: Any) -> None:
    scene.pop(IR_PROPERTY, None)
    scene.pop(REQUEST_PROPERTY, None)
    scene.pop(TRACE_PROPERTY, None)
    scene.pop(GUILD_TRACE_URL_PROPERTY, None)
    scene.pop(OPENUI_LANG_PROPERTY, None)
    scene.pop(COMPOSIO_STATUS_PROPERTY, None)
    scene.pop(CLICKHOUSE_EXPORTED_PROPERTY, None)
    scene.pop(AIRBYTE_EXPORTED_PROPERTY, None)
