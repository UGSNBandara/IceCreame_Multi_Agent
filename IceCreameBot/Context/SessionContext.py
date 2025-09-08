# app/state/session_context.py
from contextvars import ContextVar

CURRENT_SID: ContextVar[str | None] = ContextVar("CURRENT_SID", default=None)
