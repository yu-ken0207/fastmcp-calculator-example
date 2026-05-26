from __future__ import annotations

import contextvars
import functools
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, TypeVar

request_user: contextvars.ContextVar[str] = contextvars.ContextVar("request_user", default="unknown")
request_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_trace_id", default="")

logger = logging.getLogger("mcp.audit")
F = TypeVar("F", bound=Callable[..., Any])


def configure_audit_logging(log_path: str) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.propagate = False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_trace_id() -> str:
    return str(uuid.uuid4())


def audit_tool(fn: F) -> F:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        trace_id = request_trace_id.get() or new_trace_id()
        request_trace_id.set(trace_id)
        status = "success"
        try:
            result = fn(*args, **kwargs)
            return result
        except Exception:
            status = "error"
            raise
        finally:
            logger.info(
                json.dumps(
                    {
                        "timestamp": now_iso(),
                        "user_client": request_user.get(),
                        "tool_name": fn.__name__,
                        "trace_id": trace_id,
                        "execution_status": status,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

    return wrapper  # type: ignore[return-value]

