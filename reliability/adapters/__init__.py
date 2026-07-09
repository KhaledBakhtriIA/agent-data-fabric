"""Adapter registry and auto-detection.

The registry order matters only for detection: the first adapter whose
``can_parse`` returns True wins. Implemented adapters come before stubs.
"""

from __future__ import annotations

from pathlib import Path

from .base import Adapter
from .junit import JUnitAdapter
from .playwright import PlaywrightAdapter
from .pytest import PytestJsonAdapter

# Instantiated once; adapters are stateless.
ADAPTERS: list[Adapter] = [
    PlaywrightAdapter(),
    PytestJsonAdapter(),
    JUnitAdapter(),
]

# How much of the file to sniff during detection.
_SAMPLE_BYTES = 8192


def get_adapter(name: str) -> Adapter:
    """Look up an adapter by its framework name (e.g. ``"playwright"``)."""
    for adapter in ADAPTERS:
        if adapter.name == name:
            return adapter
    known = ", ".join(a.name for a in ADAPTERS)
    raise ValueError(f"Unknown framework '{name}'. Known adapters: {known}")


def detect_adapter(path: Path) -> Adapter | None:
    """Return the adapter that recognises ``path``, or None if none do."""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        sample = fh.read(_SAMPLE_BYTES)
    for adapter in ADAPTERS:
        if adapter.can_parse(path, sample):
            return adapter
    return None
