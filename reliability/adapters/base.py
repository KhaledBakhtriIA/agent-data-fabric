"""Adapter contract.

An adapter turns one framework's result file into a neutral :class:`Run`.
Everything downstream (store, analysers, CLI) only ever sees neutral models,
so adding a new framework means adding one adapter and nothing else.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..storage.models import Run

# Re-exported so adapters can do ``from .base import Adapter, truncate``.
from ..utils.text import truncate  # noqa: F401


class Adapter(ABC):
    #: short framework identifier, stored on every run (e.g. "playwright")
    name: str = "base"

    @abstractmethod
    def can_parse(self, path: Path, sample: str) -> bool:
        """Return True if this adapter recognises the given file.

        ``sample`` is the first few KB of the file, provided so detection does
        not have to re-read from disk.
        """

    @abstractmethod
    def parse(self, path: Path) -> Run:
        """Read the file and return a normalised :class:`Run`."""
