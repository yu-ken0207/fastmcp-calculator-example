from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


def _csv(values: Mapping[str, str], name: str, default: str = "") -> list[str]:
    return [item.strip() for item in values.get(name, default).split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    path: str
    log_path: str
    bearer_tokens: list[str]
    api_keys: list[str]
    allowed_origins: list[str]
    allowed_hosts: list[str]
    allowed_client_cidrs: list[str]
    trusted_proxy_cidrs: list[str]


def _read_config_file(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    config_path = Path(path)
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"MCP config file does not exist: {config_path}") from exc

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid MCP config entry on line {line_number}: expected NAME=value")
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not name.replace("_", "").isalnum():
            raise ValueError(f"Invalid MCP config name on line {line_number}: {name!r}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[name] = value
    return values


def _resolve_config_path(environment: Mapping[str, str], base_dir: Path) -> str:
    explicit_path = environment.get("MCP_CONFIG_FILE", "").strip()
    if explicit_path:
        return explicit_path

    default_path = base_dir / "config.production.env"
    if default_path.exists():
        return str(default_path)

    return ""


def load_settings(environ: Mapping[str, str] | None = None, base_dir: Path | None = None) -> Settings:
    environment = dict(os.environ if environ is None else environ)
    resolved_base_dir = Path.cwd() if base_dir is None else base_dir
    config_path = _resolve_config_path(environment, resolved_base_dir)
    values = _read_config_file(config_path) if config_path else {}
    values.update(environment)
    return Settings(
        host=values.get("MCP_HOST", "127.0.0.1"),
        port=int(values.get("MCP_PORT", "8000")),
        path=values.get("MCP_PATH", "/mcp"),
        log_path=values.get("MCP_AUDIT_LOG", "./logs/tool_calls.jsonl"),
        bearer_tokens=_csv(values, "MCP_BEARER_TOKENS"),
        api_keys=_csv(values, "MCP_API_KEYS"),
        allowed_origins=_csv(values, "MCP_ALLOWED_ORIGINS"),
        allowed_hosts=_csv(values, "MCP_ALLOWED_HOSTS", "mcp.intra.example.com,localhost,127.0.0.1"),
        allowed_client_cidrs=_csv(
            values,
            "MCP_ALLOWED_CLIENT_CIDRS",
            "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1/32",
        ),
        trusted_proxy_cidrs=_csv(values, "MCP_TRUSTED_PROXY_CIDRS", "127.0.0.1/32,172.16.0.0/12"),
    )


settings = load_settings()
