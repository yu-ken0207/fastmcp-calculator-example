# FastMCP Calculator Example

**English** | [繁體中文](README.zh-TW.md)

[![Tests](https://github.com/yu-ken0207/fastmcp-calculator-example/actions/workflows/test.yml/badge.svg)](https://github.com/yu-ken0207/fastmcp-calculator-example/actions/workflows/test.yml) [![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

A small calculator MCP server built with FastMCP that shows how to expose an MCP server on a private network safely: API key or bearer token auth, Host / Origin / client IP allowlists (proxy-aware), and a JSONL audit log with a trace ID for every tool call. Includes client setup for Claude Desktop and Codex and an Nginx HTTPS reverse proxy example.

Tools:

- `add(a, b)`
- `subtract(a, b)`
- `get_server_status()`

There is a single entry point: `server.py`.

## Main files

- `server.py`: starts the MCP HTTP server
- `mcp_server/config.py`: reads `config.production.env`
- `mcp_server/security.py`: checks the API key, Host, and client IP
- `mcp_server/audit.py`: writes `logs/tool_calls.jsonl`
- `mcp_server/tools.py`: calculator tools
- `config.production.example.env`: config template
- `nginx.conf`: Ubuntu / Nginx HTTPS reverse proxy example

## Install

### Windows 11

In Anaconda Prompt or `cmd`:

```cmd
conda create -n calculator python=3.11
conda activate calculator
pip install -r requirements.txt
mkdir logs
copy config.production.example.env config.production.env
```

### Ubuntu

```bash
sudo apt update
conda create -n calculator python=3.11
conda activate calculator
pip install -r requirements.txt
mkdir -p logs
cp config.production.example.env config.production.env
```

## Local setup and start

Edit `config.production.env` first. For local testing:

```dotenv
MCP_HOST=127.0.0.1
MCP_PORT=8000
MCP_PATH=/mcp
MCP_BEARER_TOKENS=test-token
MCP_API_KEYS=test-api-key
MCP_ALLOWED_HOSTS=localhost,127.0.0.1
MCP_ALLOWED_ORIGINS=
MCP_ALLOWED_CLIENT_CIDRS=127.0.0.1/32
MCP_TRUSTED_PROXY_CIDRS=127.0.0.1/32
MCP_AUDIT_LOG=./logs/tool_calls.jsonl
```

`config.production.env` is in `.gitignore`. Change the token and API key for real use.

Start the server:

Windows `cmd` or PowerShell

```cmd
python .\server.py
```

Ubuntu

```bash
python server.py
```

`server.py` reads `config.production.env` from the project folder automatically. Set `MCP_CONFIG_FILE` only if you want to use a different config file.

Default endpoint:

```text
http://127.0.0.1:8000/mcp
```

If opening it in a browser shows:

```json
{"error": "missing_or_invalid_token"}
```

the server is running.

## MCP client setup

These examples use the local server and `X-API-Key: test-api-key`.

### Claude Desktop

```json
{
  "mcpServers": {
    "calculator": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "X-API-Key": "test-api-key"
      }
    }
  }
}
```

### Codex

`~/.codex/config.toml`

```toml
[mcp_servers.calculator]
url = "http://127.0.0.1:8000/mcp"
http_headers = { "X-API-Key" = "test-api-key" }
```

or, for a remote server:

```toml
[mcp_servers.calculator]
url = "http://<server-ip>:8000/mcp"
http_headers = { "X-API-Key" = "test-api-key" }
```

Once connected, the client should list:

- `add`
- `subtract`
- `get_server_status`

## Using it on a private network

### 1. Direct connection test

To check that another computer can reach the server before setting up HTTPS or a reverse proxy, open port `8000` directly.

Change `config.production.env` to:

```dotenv
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp
MCP_BEARER_TOKENS=
MCP_API_KEYS=test-api-key
MCP_ALLOWED_HOSTS=localhost,127.0.0.1,<server-tailscale-ip>
MCP_ALLOWED_ORIGINS=
MCP_ALLOWED_CLIENT_CIDRS=100.64.0.0/10,127.0.0.1/32,<client-tailscale-ip>/32,<client-ip>/32
MCP_TRUSTED_PROXY_CIDRS=127.0.0.1/32
MCP_AUDIT_LOG=./logs/tool_calls.jsonl
```

To allow only one computer, set `MCP_ALLOWED_CLIENT_CIDRS` to its actual IP and Tailscale IP with `/32`, for example:

```dotenv
MCP_ALLOWED_CLIENT_CIDRS=100.101.102.103/32,192.168.1.50/32,127.0.0.1/32
```

Open the firewall on Windows:

```powershell
New-NetFirewallRule -DisplayName "Calculator MCP 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

Check the rule:

```powershell
Get-NetFirewallRule -DisplayName "Calculator MCP 8000"
```

On Ubuntu with `ufw`:

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

Test URL:

```text
http://<server-tailscale-ip>:8000/mcp
```

If the browser shows:

```json
{"error": "missing_or_invalid_token"}
```

the network, Host, and client IP checks all pass.

### 2. Production deployment

For real use, don't expose port `8000` directly. Instead:

1. Set `MCP_HOST=127.0.0.1`
2. Let the app listen only on `127.0.0.1:8000`
3. Put an HTTPS reverse proxy in front of it
4. Expose:

```text
https://mcp.intra.example.com/mcp
```

On Ubuntu, use `nginx.conf` as a starting point. On Windows, use IIS, Caddy, or Nginx for Windows.

You will also need:

- Internal DNS
- A TLS certificate
- Port `443` open in the firewall
- A real API key

## Checks and troubleshooting

### Is the config file being read?

Windows `cmd`, PowerShell, or Ubuntu:

```bash
python -c "from mcp_server.config import load_settings; s=load_settings(); print(s.host); print(s.allowed_hosts); print(s.allowed_client_cidrs)"
```

### Is the server listening on the network?

Windows:

```cmd
netstat -ano | findstr :8000
```

Ubuntu:

```bash
ss -ltnp | grep 8000
```

For the direct connection test you should see:

```text
0.0.0.0:8000
```

If you see:

```text
127.0.0.1:8000
```

the server is bound to localhost only, and other computers can't reach it.

### Minimal test with curl

The server uses MCP streamable HTTP, so `curl` must also send:

```text
Accept: text/event-stream
```

Windows PowerShell:

```powershell
curl.exe -H "X-API-Key: test-api-key" -H "Accept: text/event-stream" http://<server-tailscale-ip>:8000/mcp
```

Ubuntu:

```bash
curl -H "X-API-Key: test-api-key" -H "Accept: text/event-stream" http://<server-tailscale-ip>:8000/mcp
```

Without `Accept`, the usual response is:

```json
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}
```

The server isn't broken; the request just doesn't follow the MCP protocol.

### Common mistakes

- The config file is not in the project folder when you run `python .\server.py` or `python server.py`.
  The program reads `config.production.env` from the project folder automatically. If you keep it somewhere else, set `MCP_CONFIG_FILE`.

- `MCP_HOST` is still `127.0.0.1`.
  Only this computer can connect; other computers time out.

- `MCP_ALLOWED_HOSTS` doesn't include the Host the client actually uses.
  For example, if the client connects to `http://100.101.102.104:8000/mcp`, `MCP_ALLOWED_HOSTS` must include `100.101.102.104`.

- `MCP_ALLOWED_CLIENT_CIDRS` doesn't include the client's real source IP.
  Over Tailscale, the server usually sees the client's `100.x.x.x` address, not `192.168.x.x`.

- The firewall is open, but the server still listens only on `127.0.0.1`.
  Opening the firewall is not enough: set `MCP_HOST=0.0.0.0` and restart the server.

- An error from a browser or plain `curl` is mistaken for a broken server.
  `missing_or_invalid_token` usually means the endpoint is reachable; `Not Acceptable: Client must accept text/event-stream` usually means both the endpoint and the API key work.

### Common responses

- `missing_or_invalid_token`
  The endpoint is reachable, but there is no valid API key or bearer token.

- `host_not_allowed`
  `MCP_ALLOWED_HOSTS` doesn't include the Host used.

- `client_ip_not_allowed`
  `MCP_ALLOWED_CLIENT_CIDRS` doesn't include the client's source IP.

- `origin_not_allowed`
  The client sent an `Origin` that is not on the allowlist.

- TLS errors
  The certificate or trust chain isn't set up yet.

## Tests

```bash
pip install pytest
python -m pytest -q
```

`tests/test_server.py` starts a real server and connects with an MCP client to check: a missing or wrong key returns 401, a Host or Origin not on the allowlist returns 403, all three tools are listed, and after a call the audit log has an entry with the same trace ID. `tests/test_config.py` checks config loading. GitHub Actions runs them on every push.

## What success looks like

- `logs/tool_calls.jsonl` is created when the server starts
- The MCP client sees the three calculator tools
- After a tool call, the audit log records the tool name, trace ID, and result

## Not done yet

- No built-in way to run in the background.
  You start it by hand with `python server.py`; there is no Windows service, systemd service, or other auto-start yet.

- No finished HTTPS reverse proxy setup.
  The repo has an `nginx.conf` example, but the domain, certificate, DNS, and proxy deployment depend on your environment.

- No user roles or key management.
  Authentication is basic (`MCP_API_KEYS` / `MCP_BEARER_TOKENS`); there is no fuller permission model, key rotation, or SSO.

## License

Apache-2.0, see [LICENSE](LICENSE).
