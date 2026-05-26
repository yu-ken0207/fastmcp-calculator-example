# 團隊內網 MCP Server

這個專案會在主機上的 `calculator` conda 環境中執行 FastMCP，使用 Streamable HTTP transport，並透過本機 Nginx reverse proxy 提供內網 HTTPS 存取。

## 專案結構

- `server.py`：FastMCP 啟動入口與 ASGI app。
- `mcp_server/config.py`：環境變數設定。
- `mcp_server/security.py`：Bearer Token / API Key、IP 白名單、Host 與 Origin 驗證。
- `mcp_server/audit.py`：每次 tool call 的 JSONL audit log。
- `mcp_server/tools.py`：SQLite read-only tools 與 robot tools。
- `nginx.conf`：Nginx HTTPS reverse proxy 設定。
- `.env.example`：環境變數範本。
- `run_server.sh`：以 `conda run -n calculator` 啟動 server。

## 安全模型

FastMCP 只監聽主機的 `127.0.0.1:8000`，不直接對外提供服務。所有內網同仁都必須先經過 Nginx，再由 Nginx 轉發到本機 MCP server。

請求會依序經過這些檢查：

1. Nginx IP 白名單。
2. Nginx Origin 檢查。
3. App 端 Host 檢查。
4. App 端來源 IP 檢查。
5. App 端 Origin 檢查。
6. Bearer Token 或 `X-API-Key` 驗證。

所有 tools 預設都是 read-only。`send_nav_goal` 雖然已註冊，但只有在 `ALLOW_MUTATING_TOOLS=true` 時才會真的允許執行。

## 安裝與啟動

先安裝 Python 套件到 `calculator` conda 環境：

```bash
conda run -n calculator pip install -r requirements.txt
```

再準備設定檔：

```bash
cp .env.example .env
mkdir -p logs data
```

啟動 MCP server：

```bash
./run_server.sh
```

Nginx 請直接安裝在主機上，並將 [nginx.conf](/home/itri/Desktop/kai/nginx.conf:1) 納入你的 Nginx 設定後重新載入。

## 要給內網同仁使用時要改哪裡

主要有四個地方要改。

1. 改 [nginx.conf](/home/itri/Desktop/kai/nginx.conf:7) 的 `server_name`
   設成你們實際要給同仁連線的內網網域名稱，例如 `mcp.lab.local`。

2. 改 [nginx.conf](/home/itri/Desktop/kai/nginx.conf:11)
   把 `ssl_certificate` 和 `ssl_certificate_key` 換成你們內網憑證的實際路徑。

3. 改 [nginx.conf](/home/itri/Desktop/kai/nginx.conf:16)
   `allow` / `deny` 要調整成你們同仁實際所在的內網 CIDR，例如某個辦公室 VLAN 或 VPN 網段。

4. 改 [.env.example](/home/itri/Desktop/kai/.env.example:1) 後另存成 `.env`
   其中至少要改：
   `MCP_ALLOWED_HOSTS`：允許的 Host，例如 `mcp.lab.local`
   `MCP_ALLOWED_ORIGINS`：允許的 client Origin
   `MCP_ALLOWED_CLIENT_CIDRS`：App 端允許的來源 IP
   `MCP_BEARER_TOKENS` / `MCP_API_KEYS`：發給同仁或 Agent 的憑證
   `SQLITE_DB_PATH`：實際資料庫位置
   `ROBOT_API_BASE_URL`：實際 robot API 位址

如果是 Claude Code、Codex、Cursor、或自建 Agent 從同一個內網網域發請求，通常最少要同步改這兩組設定：

```bash
MCP_ALLOWED_HOSTS=mcp.lab.local
MCP_ALLOWED_ORIGINS=https://claude-code.lab.local,https://codex.lab.local,https://cursor.lab.local
```

## OAuth / SSO 建議

團隊正式使用時，建議把 OAuth / OIDC / SSO 放在 Nginx 前面或旁邊的認證層處理，例如 Keycloak、Azure AD、Okta、Google Workspace。

比較理想的做法是：

1. 由 reverse proxy 驗證使用者登入狀態。
2. 驗證成功後轉送 `X-Client-ID` 或其他穩定的使用者識別。
3. App 端 audit log 直接記錄這個識別。

API Key 比較適合留給自建 Agent、排程工作、或 CI。

## Audit Log

每次 tool call 都會寫入 `MCP_AUDIT_LOG` 指定的 JSONL 檔案，格式如下：

```json
{"timestamp":"...","user_client":"...","tool_name":"query_sqlite_readonly","trace_id":"...","execution_status":"success"}
```

Client 可以自己帶 `X-Trace-ID`，若沒有帶，server 會自動產生。
