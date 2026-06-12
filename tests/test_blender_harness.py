from adapters.blender.ido_blender.harness import _persist_sponsor_metadata


def test_persist_sponsor_metadata_from_execution_response() -> None:
    scene: dict[str, str] = {}
    _persist_sponsor_metadata(
        scene,
        {
            "trace": [{"step": "parse", "status": "completed"}],
            "guild_trace_url": "https://app.guild.ai/sessions/req-1",
        },
        {
            "trace": [
                {"step": "parse", "status": "completed"},
                {"step": "execute", "status": "completed"},
            ],
            "composio_status": "completed",
            "clickhouse_exported": True,
            "airbyte_context_exported": False,
            "openui_lang": "Stack(",
        },
    )

    assert scene["cad_agent_composio_status"] == "completed"
    assert scene["cad_agent_clickhouse_exported"] == "true"
    assert scene["cad_agent_guild_trace_url"] == "https://app.guild.ai/sessions/req-1"
    assert scene["cad_agent_openui_lang"] == "Stack("
