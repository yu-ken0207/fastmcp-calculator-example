# FastMCP Calculator Example

這個專案提供一個可驗證、可記錄 audit log 的 Calculator MCP server。

提供的 tools：

- `add(a, b)`
- `subtract(a, b)`
- `get_server_status()`

正式入口只有一個：`server.py`

## 主要檔案

- `server.py`：啟動 MCP HTTP server
- `mcp_server/config.py`：讀取 `config.production.env`
- `mcp_server/security.py`：驗證 API key、Host、Client IP
- `mcp_server/audit.py`：寫入 `logs/tool_calls.jsonl`
- `mcp_server/tools.py`：Calculator tools
- `config.production.example.env`：設定檔範本
- `nginx.conf`：Ubuntu / Nginx HTTPS 反向代理範例

## 安裝

### Windows 11

在 Anaconda Prompt 或 `cmd`：

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

## 本機設定與啟動

先編輯 `config.production.env`，本機測試可用：

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

`config.production.env` 已被 `.gitignore` 排除。正式環境請更換 token / API key。

啟動方式：

Windows `cmd`

```cmd
python .\server.py
```

Windows PowerShell

```powershell
python .\server.py
```

Ubuntu

```bash
python server.py
```

只要專案目錄裡有 `config.production.env`，`server.py` 會自動讀取它。  
如果你要改用別的設定檔，才需要另外指定 `MCP_CONFIG_FILE`。

預設 endpoint：

```text
http://127.0.0.1:8000/mcp
```

瀏覽器直接打開若看到：

```json
{"error": "missing_or_invalid_token"}
```

代表 server 已正常啟動。

## MCP Client 設定

以下以本機與 `X-API-Key: test-api-key` 為例。

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

[mcp_servers.calculator.headers]
X-API-Key = "test-api-key"
```

連線成功後應能列出：

- `add`
- `subtract`
- `get_server_status`

## 內網使用

### 1. 先做直連測試

如果只是先讓另一台電腦測通，不先做 HTTPS / 反向代理，可直接開 `8000`。

把 `config.production.env` 改成：

```dotenv
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_PATH=/mcp
MCP_BEARER_TOKENS=
MCP_API_KEYS=test-api-key
MCP_ALLOWED_HOSTS=localhost,127.0.0.1,伺服器主機Tailscale的IP位置
MCP_ALLOWED_ORIGINS=
MCP_ALLOWED_CLIENT_CIDRS=100.64.0.0/10,127.0.0.1/32, 允許連線主機Tailscale的IP位置/32 , 允許連線主機的IP位置/32
MCP_TRUSTED_PROXY_CIDRS=127.0.0.1/32
MCP_AUDIT_LOG=./logs/tool_calls.jsonl
```

如果你只想放行某一台電腦，請把 `MCP_ALLOWED_CLIENT_CIDRS` 改成對方實際 IP位置 和 Tailscale的IP位置加上 `/32`，例如：

```dotenv
MCP_ALLOWED_CLIENT_CIDRS=100.113.45.31/32,192.168.50.57/32,127.0.0.1/32
```

Windows 開防火牆：

```powershell
New-NetFirewallRule -DisplayName "Calculator MCP 8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000
```

確認規則：

```powershell
Get-NetFirewallRule -DisplayName "Calculator MCP 8000"
```

Ubuntu 如果使用 `ufw`：

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

直連測試網址：

```text
http://遠端主機Tailscale的IP位置:8000/mcp
```

如果瀏覽器看到：

```json
{"error": "missing_or_invalid_token"}
```

代表網路、Host、Client IP 都已經通了。

### 2. 正式部署

正式使用建議不要直接開 `8000`，而是：

1. `MCP_HOST=127.0.0.1`
2. 讓 app 只聽本機 `127.0.0.1:8000`
3. 前面放 HTTPS 反向代理
4. 對外提供：

```text
https://mcp.intra.example.com/mcp
```

Ubuntu 可用 `nginx.conf` 當範例。  
Windows 可用 IIS、Caddy 或 Windows 版 Nginx。

正式部署時要另外準備：

- 內網 DNS
- TLS 憑證
- 防火牆 `443`
- 正式 API key

## 驗證與排錯

### 先確認有沒有讀到設定檔

Windows `cmd`

```cmd
python -c "from mcp_server.config import load_settings; s=load_settings(); print(s.host); print(s.allowed_hosts); print(s.allowed_client_cidrs)"
```

Windows PowerShell

```powershell
python -c "from mcp_server.config import load_settings; s=load_settings(); print(s.host); print(s.allowed_hosts); print(s.allowed_client_cidrs)"
```

Ubuntu

```bash
python -c "from mcp_server.config import load_settings; s=load_settings(); print(s.host); print(s.allowed_hosts); print(s.allowed_client_cidrs)"
```

### 先確認是不是有對外監聽

Windows：

```cmd
netstat -ano | findstr :8000
```

Ubuntu：

```bash
ss -ltnp | grep 8000
```

直連測試時，應該看到：

```text
0.0.0.0:8000
```

如果看到的是：

```text
127.0.0.1:8000
```

代表 server 只綁本機，別台電腦一定連不到。

### 用 curl 做最低限度測試

這個 server 使用 MCP streamable HTTP，所以 `curl` 也要帶：

```text
Accept: text/event-stream
```

Windows PowerShell：

```powershell
curl.exe -H "X-API-Key: test-api-key" -H "Accept: text/event-stream" http://Tailscale的IP位置:8000/mcp
```

Ubuntu：

```bash
curl -H "X-API-Key: test-api-key" -H "Accept: text/event-stream" http://Tailscale的IP位置:8000/mcp
```

如果沒有帶 `Accept`，常見回應是：

```json
{"jsonrpc":"2.0","id":"server-error","error":{"code":-32600,"message":"Not Acceptable: Client must accept text/event-stream"}}
```

這不是 server 壞掉，而是測試方式不符合 MCP 協定。

### 常見錯誤

- 設定檔不在專案目錄，卻直接執行 `python .\server.py` 或 `python server.py`
  目前程式會自動讀取專案目錄裡的 `config.production.env`。如果你把設定檔放到別的路徑，才需要另外指定 `MCP_CONFIG_FILE`。

- `MCP_HOST` 仍是 `127.0.0.1`
  只會本機可連，別台電腦會 timeout。

- `MCP_ALLOWED_HOSTS` 沒包含實際連線的 Host
  例如對方連 `http://100.76.50.123:8000/mcp`，那 `MCP_ALLOWED_HOSTS` 至少要包含 `100.76.50.123`。

- `MCP_ALLOWED_CLIENT_CIDRS` 沒放進對方真正的來源 IP
  經過 Tailscale 時，server 常看到的是對方的 `100.x.x.x` 位址，不一定是 `192.168.x.x`。

- 防火牆已開，但 server 還是只在 `127.0.0.1` 監聽
  防火牆放行不等於可連線，還要確認 `MCP_HOST=0.0.0.0` 且 server 已重啟。

- 瀏覽器或普通 `curl` 的錯誤被誤判成 server 壞掉
  `missing_or_invalid_token` 常表示站台已通；`Not Acceptable: Client must accept text/event-stream` 常表示站台與 API key 都已通。

### 常見回應

- `missing_or_invalid_token`
  endpoint 可達，但沒有有效 API key 或 Bearer token。

- `host_not_allowed`
  `MCP_ALLOWED_HOSTS` 沒包含實際連線的 Host。

- `client_ip_not_allowed`
  `MCP_ALLOWED_CLIENT_CIDRS` 沒包含對方實際來源 IP。

- `origin_not_allowed`
  client 有帶 `Origin`，但不在允許清單中。

- TLS 錯誤
  憑證或信任鏈尚未設定完成。

## 成功標準

- server 啟動後建立 `logs/tool_calls.jsonl`
- MCP client 能看見三個 calculator tools
- 呼叫 tool 後 audit log 會寫入 tool name、trace id 與結果

## 目前還沒做到的

- 還沒有內建背景常駐機制
  目前仍是手動執行 `python server.py` 啟動，尚未做成 Windows Service、systemd service 或其他自動常駐方式。

- 還沒有正式的 HTTPS 反向代理成品
  repo 內有 `nginx.conf` 範例，但實際的網域、憑證、DNS 與反向代理部署仍需依環境完成。

- 還沒有使用者分級或金鑰管理機制
  目前是以 `MCP_API_KEYS` / `MCP_BEARER_TOKENS` 做基本驗證，尚未整合更完整的權限管理、金鑰輪替或 SSO。

- 還沒有更完整的自動化測試
  現在的測試主要覆蓋設定載入與基本 calculator tools，尚未涵蓋完整的 HTTP / MCP client 整合測試。
