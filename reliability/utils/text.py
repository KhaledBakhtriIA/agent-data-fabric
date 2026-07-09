"""Text helpers."""

from __future__ import annotations

from typing import Optional


def truncate(message: Optional[str], limit: int = 500) -> Optional[str]:
    """Keep stored error messages short; full detail stays in the source file.

    We never want to bloat the history DB (or accidentally store secrets echoed
    into a long stack trace), so messages are capped.
    """
    if not message:
        return None
    message = message.strip()
    return message[:limit] if message else None
