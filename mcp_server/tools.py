from __future__ import annotations

import json
import re
import sqlite3
import urllib.error
import urllib.request
from typing import Any

from .audit import audit_tool, now_iso, request_trace_id
from .config import Settings

READONLY_SQL_PREFIXES = ("select", "with", "pragma", "explain")
BLOCKED_SQL_KEYWORDS = {
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "replace",
    "update",
    "vacuum",
    "alter",
}


def register_tools(mcp: Any, settings: Settings) -> None:
    @mcp.tool
    @audit_tool
    def describe_schema() -> dict[str, Any]:
        """Describe the configured SQLite database schema without returning data rows."""
        conn = _readonly_conn(settings.sqlite_db_path)
        try:
            rows = conn.execute(
                """
                SELECT type, name, tbl_name, sql
                FROM sqlite_master
                WHERE type IN ('table', 'view', 'index')
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY type, name
                """
            ).fetchall()
            return _ok({"objects": [dict(row) for row in rows]})
        finally:
            conn.close()

    @mcp.tool
    @audit_tool
    def validate_sql(sql: str) -> dict[str, Any]:
        """Validate that SQL appears read-only and can be explained by SQLite."""
        try:
            _assert_readonly_sql(sql)
        except ValueError as exc:
            return _ok({"valid": False, "read_only": False, "error": str(exc)})

        conn = _readonly_conn(settings.sqlite_db_path)
        try:
            conn.execute(f"EXPLAIN QUERY PLAN {sql}")
            return _ok({"valid": True, "read_only": True})
        except sqlite3.Error as exc:
            return _ok({"valid": False, "read_only": True, "error": str(exc)})
        finally:
            conn.close()

    @mcp.tool
    @audit_tool
    def query_sqlite_readonly(sql: str, params: list[Any] | None = None, limit: int = 100) -> dict[str, Any]:
        """Run a bounded read-only SQLite query."""
        _assert_readonly_sql(sql)
        limit = max(1, min(limit, 500))
        conn = _readonly_conn(settings.sqlite_db_path)
        try:
            cursor = conn.execute(sql, params or [])
            rows = cursor.fetchmany(limit)
            return _ok(
                {
                    "columns": [description[0] for description in cursor.description or []],
                    "rows": [dict(row) for row in rows],
                    "limit": limit,
                }
            )
        finally:
            conn.close()

    @mcp.tool
    @audit_tool
    def get_robot_pose() -> dict[str, Any]:
        """Read the robot's current pose from the internal robot API."""
        return _robot_get(settings, "/pose")

    @mcp.tool
    @audit_tool
    def get_nav_status() -> dict[str, Any]:
        """Read the robot navigation status from the internal robot API."""
        return _robot_get(settings, "/nav/status")

    @mcp.tool
    @audit_tool
    def send_nav_goal(x: float, y: float, yaw: float) -> dict[str, Any]:
        """Send a navigation goal. Disabled unless ALLOW_MUTATING_TOOLS=true."""
        if not settings.allow_mutating_tools:
            raise PermissionError("send_nav_goal is disabled because tools are read-only by default")
        return _robot_post(settings, "/nav/goal", {"x": x, "y": y, "yaw": yaw})


def _ok(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "trace_id": request_trace_id.get(),
        "timestamp": now_iso(),
        **payload,
    }


def _readonly_conn(path: str) -> sqlite3.Connection:
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    return conn


def _assert_readonly_sql(sql: str) -> None:
    normalized = " ".join(sql.strip().lower().split())
    if not normalized.startswith(READONLY_SQL_PREFIXES):
        raise ValueError("only read-only SQL is allowed")
    if ";" in normalized.rstrip(";"):
        raise ValueError("multiple SQL statements are not allowed")
    if "pragma writable_schema" in normalized:
        raise ValueError("SQL contains a blocked pragma")
    tokens = set(re.findall(r"[a-z_]+", normalized))
    if tokens.intersection(BLOCKED_SQL_KEYWORDS):
        raise ValueError("SQL contains a blocked keyword")


def _robot_get(settings: Settings, path: str) -> dict[str, Any]:
    if not settings.robot_api_base_url:
        return _ok({"available": False, "reason": "ROBOT_API_BASE_URL is not configured"})
    return _robot_request("GET", settings.robot_api_base_url + path)


def _robot_post(settings: Settings, path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.robot_api_base_url:
        return _ok({"available": False, "reason": "ROBOT_API_BASE_URL is not configured"})
    return _robot_request("POST", settings.robot_api_base_url + path, payload)


def _robot_request(method: str, url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8")
            return _ok({"available": True, "response": json.loads(body) if body else None})
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return _ok({"available": False, "error": str(exc)})
