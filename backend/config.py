from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    provider: str
    demo_mode: bool
    openai_model: str
    log_level: str
    guild_trace_enabled: bool
    guild_otlp_endpoint: str | None
    guild_api_key: str | None
    guild_workspace_id: str | None
    guild_trace_view_url_template: str
    guild_service_name: str
    guild_export_timeout: float
    clickhouse_enabled: bool
    clickhouse_host: str | None
    clickhouse_port: int
    clickhouse_database: str
    clickhouse_table: str
    clickhouse_username: str
    clickhouse_password: str | None
    clickhouse_secure: bool
    clickhouse_auto_create_table: bool
    clickhouse_export_timeout: float
    composio_enabled: bool
    composio_api_key: str | None
    composio_user_id: str
    composio_tool_slug: str
    composio_export_timeout: float
    pioneer_model_id: str
    airbyte_enabled: bool
    airbyte_context_dir: str | None
    airbyte_context_endpoint: str | None
    airbyte_api_key: str | None
    airbyte_export_timeout: float

    @classmethod
    def from_env(cls) -> Settings:
        workspace_id = os.getenv("GUILD_WORKSPACE_ID", "").strip() or None
        return cls(
            provider=os.getenv("CAD_AGENT_PROVIDER", "openai").strip().lower(),
            demo_mode=_env_bool("CAD_AGENT_DEMO_MODE"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.5"),
            log_level=os.getenv("CAD_AGENT_LOG_LEVEL", "INFO").upper(),
            guild_trace_enabled=_env_bool("GUILD_TRACE_ENABLED"),
            guild_otlp_endpoint=os.getenv("GUILD_OTLP_ENDPOINT", "").strip() or None,
            guild_api_key=os.getenv("GUILD_API_KEY", "").strip() or None,
            guild_workspace_id=workspace_id,
            guild_trace_view_url_template=os.getenv(
                "GUILD_TRACE_VIEW_URL",
                "https://app.guild.ai/workspaces/{workspace_id}/sessions/{request_id}",
            ),
            guild_service_name=os.getenv("GUILD_SERVICE_NAME", "cad-agent-api"),
            guild_export_timeout=float(os.getenv("GUILD_EXPORT_TIMEOUT", "10")),
            clickhouse_enabled=_env_bool("CLICKHOUSE_ENABLED"),
            clickhouse_host=os.getenv("CLICKHOUSE_HOST", "").strip() or None,
            clickhouse_port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
            clickhouse_database=os.getenv("CLICKHOUSE_DATABASE", "default"),
            clickhouse_table=os.getenv("CLICKHOUSE_TABLE", "cad_agent_traces"),
            clickhouse_username=os.getenv("CLICKHOUSE_USERNAME", "default"),
            clickhouse_password=os.getenv("CLICKHOUSE_PASSWORD", "").strip() or None,
            clickhouse_secure=_env_bool("CLICKHOUSE_SECURE"),
            clickhouse_auto_create_table=_env_bool("CLICKHOUSE_AUTO_CREATE_TABLE", True),
            clickhouse_export_timeout=float(os.getenv("CLICKHOUSE_EXPORT_TIMEOUT", "10")),
            composio_enabled=_env_bool("COMPOSIO_ENABLED"),
            composio_api_key=os.getenv("COMPOSIO_API_KEY", "").strip() or None,
            composio_user_id=os.getenv("COMPOSIO_USER_ID", "cad-agent-user"),
            composio_tool_slug=os.getenv("COMPOSIO_TOOL_SLUG", "").strip(),
            composio_export_timeout=float(os.getenv("COMPOSIO_EXPORT_TIMEOUT", "15")),
            pioneer_model_id=os.getenv("PIONEER_MODEL_ID", "gpt-4o"),
            airbyte_enabled=_env_bool("AIRBYTE_ENABLED"),
            airbyte_context_dir=os.getenv("AIRBYTE_CONTEXT_DIR", "").strip() or None,
            airbyte_context_endpoint=os.getenv("AIRBYTE_CONTEXT_ENDPOINT", "").strip() or None,
            airbyte_api_key=os.getenv("AIRBYTE_API_KEY", "").strip() or None,
            airbyte_export_timeout=float(os.getenv("AIRBYTE_EXPORT_TIMEOUT", "10")),
        )
