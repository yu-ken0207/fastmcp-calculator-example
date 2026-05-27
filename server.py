from __future__ import annotations

from fastmcp import FastMCP
from starlette.middleware import Middleware

from mcp_server.audit import configure_audit_logging
from mcp_server.config import settings
from mcp_server.security import SecurityMiddleware
from mcp_server.tools import register_tools


configure_audit_logging(settings.log_path)

mcp = FastMCP("Calculator MCP")
register_tools(mcp)

middleware = [
    Middleware(
        SecurityMiddleware,
        bearer_tokens=settings.bearer_tokens,
        api_keys=settings.api_keys,
        allowed_origins=settings.allowed_origins,
        allowed_hosts=settings.allowed_hosts,
        allowed_client_cidrs=settings.allowed_client_cidrs,
        trusted_proxy_cidrs=settings.trusted_proxy_cidrs,
    )
]

app = mcp.http_app(path=settings.path, middleware=middleware, transport="streamable-http")


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=settings.host,
        port=settings.port,
        path=settings.path,
        middleware=middleware,
    )
