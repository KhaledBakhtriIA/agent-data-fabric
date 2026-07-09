"""Text helpers."""

from __future__ import annotations


def truncate(message: str | None, limit: int = 500) -> str | None:
    """Keep stored error messages short; full detail stays in the source file.

    We never want to bloat the history DB (or accidentally store secrets echoed
    into a long stack trace), so messages are capped.
    """
    if not message:
        return None
    message = message.strip()
    return message[:limit] if message else None
