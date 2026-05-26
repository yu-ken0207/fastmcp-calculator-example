from __future__ import annotations

import os
from dataclasses import dataclass


def _csv(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    server_name: str = os.getenv("MCP_SERVER_NAME", "Internal Team MCP")
    host: str = os.getenv("MCP_HOST", "127.0.0.1")
    port: int = int(os.getenv("MCP_PORT", "8000"))
    path: str = os.getenv("MCP_PATH", "/mcp")
    log_path: str = os.getenv("MCP_AUDIT_LOG", "./logs/tool_calls.jsonl")
    bearer_tokens: list[str] = None
    api_keys: list[str] = None
    allowed_origins: list[str] = None
    allowed_hosts: list[str] = None
    allowed_client_cidrs: list[str] = None
    trusted_proxy_cidrs: list[str] = None
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "./data/app.db")
    robot_api_base_url: str = os.getenv("ROBOT_API_BASE_URL", "")
    allow_mutating_tools: bool = os.getenv("ALLOW_MUTATING_TOOLS", "false").lower() == "true"

    def __post_init__(self) -> None:
        object.__setattr__(self, "bearer_tokens", _csv("MCP_BEARER_TOKENS"))
        object.__setattr__(self, "api_keys", _csv("MCP_API_KEYS"))
        object.__setattr__(self, "allowed_origins", _csv("MCP_ALLOWED_ORIGINS"))
        object.__setattr__(self, "allowed_hosts", _csv("MCP_ALLOWED_HOSTS", "mcp.intra.example.com,localhost,127.0.0.1"))
        object.__setattr__(
            self,
            "allowed_client_cidrs",
            _csv("MCP_ALLOWED_CLIENT_CIDRS", "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32"),
        )
        object.__setattr__(self, "trusted_proxy_cidrs", _csv("MCP_TRUSTED_PROXY_CIDRS", "127.0.0.1/32,172.16.0.0/12"))


settings = Settings()
