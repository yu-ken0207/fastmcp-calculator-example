from __future__ import annotations

import hmac
import ipaddress
import json

from starlette.types import ASGIApp, Receive, Scope, Send

from .audit import new_trace_id, request_trace_id, request_user


class SecurityMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        bearer_tokens: list[str],
        api_keys: list[str],
        allowed_origins: list[str],
        allowed_hosts: list[str],
        allowed_client_cidrs: list[str],
        trusted_proxy_cidrs: list[str],
    ) -> None:
        self.app = app
        self.bearer_tokens = bearer_tokens
        self.api_keys = api_keys
        self.allowed_origins = allowed_origins
        self.allowed_hosts = allowed_hosts
        self.allowed_client_networks = [ipaddress.ip_network(cidr) for cidr in allowed_client_cidrs]
        self.trusted_proxy_networks = [ipaddress.ip_network(cidr) for cidr in trusted_proxy_cidrs]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.decode("latin1").lower(): value.decode("latin1") for key, value in scope["headers"]}
        client_ip = self._client_ip(scope, headers)

        host = headers.get("host", "").split(":")[0]
        if self.allowed_hosts and host not in self.allowed_hosts:
            await self._reject(send, 403, "host_not_allowed")
            return

        if not self._ip_allowed(client_ip):
            await self._reject(send, 403, "client_ip_not_allowed")
            return

        origin = headers.get("origin")
        if origin and self.allowed_origins and origin not in self.allowed_origins:
            await self._reject(send, 403, "origin_not_allowed")
            return

        user = self._authenticated_user(headers)
        if not user:
            await self._reject(send, 401, "missing_or_invalid_token")
            return

        user_token = request_user.set(user)
        trace_token = request_trace_id.set(headers.get("x-trace-id") or new_trace_id())
        try:
            await self.app(scope, receive, send)
        finally:
            request_user.reset(user_token)
            request_trace_id.reset(trace_token)

    def _client_ip(self, scope: Scope, headers: dict[str, str]) -> str:
        peer = scope.get("client") or ("127.0.0.1", 0)
        peer_ip = peer[0]
        if self._ip_in_networks(peer_ip, self.trusted_proxy_networks):
            forwarded_for = headers.get("x-forwarded-for", "")
            if forwarded_for:
                return forwarded_for.split(",")[0].strip()
        return peer_ip

    def _ip_allowed(self, ip: str) -> bool:
        return self._ip_in_networks(ip, self.allowed_client_networks)

    @staticmethod
    def _ip_in_networks(ip: str, networks: list[ipaddress._BaseNetwork]) -> bool:
        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            return False
        return any(address in network for network in networks)

    def _authenticated_user(self, headers: dict[str, str]) -> str | None:
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if self._token_allowed(token, self.bearer_tokens):
                return headers.get("x-client-id") or "bearer-client"

        api_key = headers.get("x-api-key", "")
        if api_key and self._token_allowed(api_key, self.api_keys):
            return headers.get("x-client-id") or "api-key-client"
        return None

    @staticmethod
    def _token_allowed(candidate: str, allowed: list[str]) -> bool:
        return bool(candidate) and any(hmac.compare_digest(candidate, token) for token in allowed)

    @staticmethod
    async def _reject(send: Send, status_code: int, reason: str) -> None:
        body = json.dumps({"error": reason}).encode("utf-8")
        headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))]
        if status_code == 401:
            headers.append((b"www-authenticate", b"Bearer"))
        await send({"type": "http.response.start", "status": status_code, "headers": headers})
        await send({"type": "http.response.body", "body": body})
