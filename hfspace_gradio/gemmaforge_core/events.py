"""In-memory event sink for the Space (replaces the file/stderr sink used by the CLI)."""
from __future__ import annotations

import time
from typing import Callable, Optional


SCHEMA_EVENTS = "gemmaforge.events/v1"


class MemoryEventSink:
    """Collects events in a list. Optional callback fires after each emit (e.g. for progress)."""

    def __init__(self, on_emit: Optional[Callable[[dict], None]] = None) -> None:
        self.events: list[dict] = []
        self._on_emit = on_emit

    def emit(self, kind: str, **fields: object) -> None:
        rec = {"schema": SCHEMA_EVENTS, "ts": time.time(), "kind": kind, **fields}
        self.events.append(rec)
        if self._on_emit is not None:
            try:
                self._on_emit(rec)
            except Exception:
                pass

    def close(self) -> None:
        return

    @property
    def enabled(self) -> bool:
        return True
