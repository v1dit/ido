from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from shared.contracts import TraceEvent

logger = logging.getLogger("cad_agent.clickhouse")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS {table} (
    request_id String,
    step String,
    status String,
    duration_ms Nullable(Float64),
    prompt Nullable(String),
    target_tool Nullable(String),
    metadata String,
    exported_at DateTime64(3, 'UTC')
) ENGINE = MergeTree
ORDER BY (request_id, step)
"""


@dataclass(frozen=True)
class ClickHouseExportResult:
    exported: bool
    rows: int = 0
    error: str | None = None


class ClickHouseTraceExporter:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        database: str,
        table: str,
        username: str = "default",
        password: str = "",
        secure: bool = False,
        auto_create_table: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self._host = host
        self._port = port
        self._database = database
        self._table = table
        self._username = username
        self._password = password
        self._secure = secure
        self._auto_create_table = auto_create_table
        self._timeout = timeout
        self._table_ready = False
        self._exported_counts: dict[str, int] = {}

    @property
    def enabled(self) -> bool:
        return bool(self._host)

    async def export(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None = None,
        target_tool: str | None = None,
        scene_snapshot: dict[str, Any] | None = None,
    ) -> ClickHouseExportResult:
        if not self.enabled or not events:
            return ClickHouseExportResult(exported=False)

        prior = self._exported_counts.get(request_id, 0)
        new_events = events[prior:]
        if not new_events:
            return ClickHouseExportResult(exported=True, rows=0)

        rows = []
        for event in new_events:
            metadata = dict(event.metadata)
            if scene_snapshot:
                metadata["scene"] = scene_snapshot
            rows.append(
                {
                    "request_id": request_id,
                    "step": event.step,
                    "status": event.status,
                    "duration_ms": event.duration_ms,
                    "prompt": prompt,
                    "target_tool": target_tool,
                    "metadata": json.dumps(metadata, sort_keys=True),
                    "exported_at": datetime.now(timezone.utc)
                    .replace(tzinfo=None)
                    .isoformat(timespec="milliseconds"),
                }
            )
        try:
            await asyncio.to_thread(self._insert_rows, rows)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            logger.warning("clickhouse export failed for %s: %s", request_id, exc)
            return ClickHouseExportResult(exported=False, error=str(exc))

        self._exported_counts[request_id] = len(events)
        logger.info(
            "clickhouse trace exported request_id=%s rows=%d",
            request_id,
            len(rows),
        )
        return ClickHouseExportResult(exported=True, rows=len(rows))

    async def ping(self) -> bool:
        if not self.enabled:
            return False
        try:
            await asyncio.to_thread(self._command, "SELECT 1")
            return True
        except (HTTPError, URLError, TimeoutError, OSError):
            return False

    async def query_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.enabled:
            return []
        return await asyncio.to_thread(self._query_recent, limit)

    def _query_recent(self, limit: int) -> list[dict[str, Any]]:
        query = (
            f"SELECT request_id, step, status, duration_ms, prompt, target_tool, exported_at "
            f"FROM {self._table} ORDER BY exported_at DESC LIMIT {int(limit)} FORMAT JSONEachRow"
        )
        body = self._post(query, b"", read_body=True)
        if not body.strip():
            return []
        return [json.loads(line) for line in body.splitlines() if line.strip()]

    def _insert_rows(self, rows: list[dict[str, Any]]) -> None:
        if self._auto_create_table and not self._table_ready:
            self._command(CREATE_TABLE_SQL.format(table=self._table))
            self._table_ready = True

        payload = "\n".join(json.dumps(row) for row in rows)
        query = f"INSERT INTO {self._table} FORMAT JSONEachRow"
        self._post(query, payload.encode("utf-8"))

    def _command(self, sql: str) -> None:
        self._post(sql, b"")

    def _post(self, query: str, body: bytes, *, read_body: bool = False) -> str:
        scheme = "https" if self._secure else "http"
        url = (
            f"{scheme}://{self._host}:{self._port}/"
            f"?database={quote(self._database)}&query={quote(query)}"
        )
        headers = {"Content-Type": "application/json"}
        if self._username or self._password:
            token = base64.b64encode(
                f"{self._username}:{self._password}".encode("utf-8")
            ).decode("ascii")
            headers["Authorization"] = f"Basic {token}"

        request = Request(url, data=body or None, method="POST", headers=headers)
        with urlopen(request, timeout=self._timeout) as response:
            if getattr(response, "status", 200) >= 400:
                raise HTTPError(
                    url,
                    response.status,
                    response.reason,
                    response.headers,
                    None,
                )
            if read_body:
                return response.read().decode("utf-8")
            return ""


class NullClickHouseTraceExporter(ClickHouseTraceExporter):
    def __init__(self) -> None:
        super().__init__(host="", port=8123, database="default", table="cad_agent_traces")

    @property
    def enabled(self) -> bool:
        return False

    async def export(
        self,
        request_id: str,
        events: list[TraceEvent],
        *,
        prompt: str | None = None,
        target_tool: str | None = None,
        scene_snapshot: dict[str, Any] | None = None,
    ) -> ClickHouseExportResult:
        return ClickHouseExportResult(exported=False)

    async def ping(self) -> bool:
        return False

    async def query_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return []


def create_clickhouse_exporter(settings: Any) -> ClickHouseTraceExporter:
    if not settings.clickhouse_enabled or not settings.clickhouse_host:
        return NullClickHouseTraceExporter()
    return ClickHouseTraceExporter(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        database=settings.clickhouse_database,
        table=settings.clickhouse_table,
        username=settings.clickhouse_username,
        password=settings.clickhouse_password or "",
        secure=settings.clickhouse_secure,
        auto_create_table=settings.clickhouse_auto_create_table,
        timeout=settings.clickhouse_export_timeout,
    )
