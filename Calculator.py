from fastmcp import FastMCP
from datetime import datetime
import uuid

# 建立 MCP Server
mcp = FastMCP("Simple Calculator MCP")


# -----------------------------
# Tool 1: 加法
# -----------------------------
@mcp.tool
def add(a: float, b: float) -> dict:
    """
    Add two numbers together.
    """

    result = a + b

    return {
        "status": "success",
        "operation": "add",
        "a": a,
        "b": b,
        "result": result,
        "trace_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat()
    }


# -----------------------------
# Tool 2: 減法
# -----------------------------
@mcp.tool
def subtract(a: float, b: float) -> dict:
    """
    Subtract b from a.
    """

    result = a - b

    return {
        "status": "success",
        "operation": "subtract",
        "a": a,
        "b": b,
        "result": result,
        "trace_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat()
    }


# -----------------------------
# Tool 3: Server 狀態
# -----------------------------
@mcp.tool
def get_server_status() -> dict:
    """
    Get MCP server status.
    """

    return {
        "status": "online",
        "server_name": "Simple Calculator MCP",
        "timestamp": datetime.now().isoformat()
    }


# -----------------------------
# 啟動 Server
# -----------------------------
if __name__ == "__main__":

    # 本機 HTTP MCP
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        path="/mcp"
    )