"""ND-JSON event sink used by ``src/scan.py`` and ``src/stream_with_probe.py``.

Schema id: ``gemmaforge.events/v1``. See ``docs/events.md`` for the full set
of event kinds. Consumers (e.g. the pwnkit live dashboard) tail the resulting
file or stream and subscribe by ``kind``.
"""
from __future__ import annotations

import json
import sys
import time
from typing import IO, Optional


SCHEMA_EVENTS = "gemmaforge.events/v1"


class EventSink:
    """Writes ND-JSON events. ``None`` disables, ``-`` routes to stderr, else file (append)."""

    def __init__(self, target: Optional[str]) -> None:
        self._fp: Optional[IO[str]]
        self._owns: bool
        if target is None:
            self._fp = None
            self._owns = False
        elif target == "-":
            self._fp = sys.stderr
            self._owns = False
        else:
            self._fp = open(target, "a", encoding="utf-8")
            self._owns = True

    def emit(self, kind: str, **fields: object) -> None:
        if self._fp is None:
            return
        rec = {"schema": SCHEMA_EVENTS, "ts": time.time(), "kind": kind, **fields}
        self._fp.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fp.flush()

    def close(self) -> None:
        if self._owns and self._fp is not None:
            self._fp.close()

    @property
    def enabled(self) -> bool:
        return self._fp is not None
