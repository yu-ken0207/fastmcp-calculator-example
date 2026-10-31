"""實際開起 MCP server，用 MCP 客戶端連上去：驗證、白名單、工具、稽核紀錄。"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

ROOT = Path(__file__).resolve().parent.parent
API_KEY = "test-api-key"
ORIGIN = "https://app.example.com"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("mcp")
    port = _free_port()
    audit = tmp / "logs" / "tool_calls.jsonl"
    env = {
        **os.environ,
        "MCP_CONFIG_FILE": "",
        "MCP_HOST": "127.0.0.1",
        "MCP_PORT": str(port),
        "MCP_PATH": "/mcp",
        "MCP_BEARER_TOKENS": "",
        "MCP_API_KEYS": API_KEY,
        "MCP_ALLOWED_HOSTS": "localhost,127.0.0.1",
        "MCP_ALLOWED_ORIGINS": ORIGIN,
        "MCP_ALLOWED_CLIENT_CIDRS": "127.0.0.1/32",
        "MCP_TRUSTED_PROXY_CIDRS": "127.0.0.1/32",
        "MCP_AUDIT_LOG": str(audit),
    }
    # 在暫存資料夾執行，不會讀到專案裡的 config.production.env
    out = open(tmp / "server.out", "w")
    proc = subprocess.Popen([sys.executable, str(ROOT / "server.py")], cwd=tmp, env=env, stdout=out, stderr=subprocess.STDOUT)
    url = f"http://127.0.0.1:{port}/mcp"
    deadline = time.time() + 30
    while True:
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except urllib.error.HTTPError:
            break  # 有回應（例如 401）就是開好了
        except OSError:
            if proc.poll() is not None or time.time() > deadline:
                out.close()
                pytest.fail("server 沒有開起來：\n" + (tmp / "server.out").read_text())
            time.sleep(0.3)
    yield url, audit
    proc.terminate()
    proc.wait(10)
    out.close()


def _status(url: str, headers: dict[str, str]) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"Accept": "text/event-stream", **headers})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def test_rejects_missing_or_wrong_key(server):
    url, _ = server
    assert _status(url, {}) == (401, '{"error": "missing_or_invalid_token"}')
    assert _status(url, {"X-API-Key": "wrong"})[0] == 401


def test_rejects_unknown_host_and_origin(server):
    url, _ = server
    code, body = _status(url, {"X-API-Key": API_KEY, "Host": "evil.example.com"})
    assert (code, "host_not_allowed" in body) == (403, True)
    code, body = _status(url, {"X-API-Key": API_KEY, "Origin": "https://evil.example.com"})
    assert (code, "origin_not_allowed" in body) == (403, True)


def test_tools_and_audit_log(server):
    url, audit = server

    async def run():
        transport = StreamableHttpTransport(url, headers={"X-API-Key": API_KEY})
        async with Client(transport) as client:
            tools = sorted(t.name for t in await client.list_tools())
            added = await client.call_tool("add", {"a": 2, "b": 3})
            subtracted = await client.call_tool("subtract", {"a": 2, "b": 3})
            return tools, added.data, subtracted.data

    tools, added, subtracted = asyncio.run(run())
    assert tools == ["add", "get_server_status", "subtract"]
    assert (added["status"], added["result"]) == ("success", 5.0)
    assert subtracted["result"] == -1.0

    entries = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    add_entry = next(e for e in entries if e["tool_name"] == "add")
    assert add_entry["execution_status"] == "success"
    assert add_entry["trace_id"] == added["trace_id"]
