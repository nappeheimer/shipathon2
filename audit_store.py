# audit_store.py
# Simple in-memory store for the last 20 audit logs.
# webhook_agent.py writes here after each run; the UI routes read from here.

from collections import deque
from typing import Optional, Dict, Any

_store: deque = deque(maxlen=20)


def save_log(log: Dict[str, Any]) -> None:
    """Called by the orchestrator after every workflow run."""
    _store.appendleft(log)


def get_latest() -> Optional[Dict[str, Any]]:
    """Returns the most recent audit log, or None if no runs yet."""
    return _store[0] if _store else None


def get_all() -> list:
    """Returns all stored logs, newest first."""
    return list(_store)