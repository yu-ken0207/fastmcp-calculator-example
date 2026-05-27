from __future__ import annotations

from typing import Any

from .audit import audit_tool, now_iso, request_trace_id


@audit_tool
def add(a: float, b: float) -> dict[str, Any]:
    """Add two numbers together."""
    return _result("add", a, b, a + b)


@audit_tool
def subtract(a: float, b: float) -> dict[str, Any]:
    """Subtract b from a."""
    return _result("subtract", a, b, a - b)


@audit_tool
def get_server_status() -> dict[str, Any]:
    """Get calculator MCP server status."""
    return {
        "status": "online",
        "server_name": "Calculator MCP",
        "trace_id": request_trace_id.get(),
        "timestamp": now_iso(),
    }


def register_tools(mcp: Any) -> None:
    mcp.tool(add)
    mcp.tool(subtract)
    mcp.tool(get_server_status)


def _result(operation: str, a: float, b: float, result: float) -> dict[str, Any]:
    return {
        "status": "success",
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
        "trace_id": request_trace_id.get(),
        "timestamp": now_iso(),
    }
