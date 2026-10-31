"""設定檔讀取：註解、引號、環境變數蓋過設定檔、格式錯誤。"""

from __future__ import annotations

import pytest

from mcp_server.config import load_settings


def test_reads_config_file_and_env_overrides(tmp_path):
    cfg = tmp_path / "config.production.env"
    cfg.write_text(
        "# 註解\n"
        "MCP_HOST=0.0.0.0\n"
        "MCP_PORT=9000\n"
        'MCP_API_KEYS="key-a, key-b"\n'
        "MCP_ALLOWED_CLIENT_CIDRS=100.101.102.103/32,127.0.0.1/32\n",
        encoding="utf-8",
    )
    s = load_settings(environ={"MCP_PORT": "9100"}, base_dir=tmp_path)
    assert s.host == "0.0.0.0"
    assert s.port == 9100  # 環境變數優先
    assert s.api_keys == ["key-a", "key-b"]
    assert s.allowed_client_cidrs == ["100.101.102.103/32", "127.0.0.1/32"]


def test_explicit_config_path(tmp_path):
    cfg = tmp_path / "other.env"
    cfg.write_text("MCP_PATH=/tools\n", encoding="utf-8")
    s = load_settings(environ={"MCP_CONFIG_FILE": str(cfg)}, base_dir=tmp_path / "nowhere")
    assert s.path == "/tools"


def test_defaults_without_config(tmp_path):
    s = load_settings(environ={}, base_dir=tmp_path)
    assert (s.host, s.port, s.path) == ("127.0.0.1", 8000, "/mcp")
    assert s.api_keys == []


@pytest.mark.parametrize("line", ["NOT_A_SETTING", "BAD-NAME=1"])
def test_rejects_malformed_lines(tmp_path, line):
    cfg = tmp_path / "config.production.env"
    cfg.write_text(line + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_settings(environ={}, base_dir=tmp_path)
