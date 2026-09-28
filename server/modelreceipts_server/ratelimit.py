"""In-memory token-bucket rate limiting (per contributor).

Two layers protect the ingest endpoint (feasibility report, risk #3):

* ``TokenBucket``: each contributor (verified key hash, or the legacy/anonymous
  identity) may submit ``burst`` records at once and ``per_hour`` records per
  hour on average. State is in memory and resets when the server restarts.
* Per-cell daily cap (in ``app.py``, backed by the database): one contributor
  may add at most ``cell_daily_cap`` records to the same
  (L1, L2, model, harness) cell within 24 hours, so a single key cannot fill a
  long-tail cell by itself.
* Newcomer budget (in ``app.py``): contributors with no stored record share ONE
  bucket (``new_contributors_per_hour`` / ``new_contributor_burst``). Without it,
  generating a new key per request would get a fresh ``burst`` every time.

Aggregation adds a third layer: a cell is not published when one contributor
supplies more than ``max_contributor_share`` of its records.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimits:
    per_hour: float = 120.0
    burst: int = 30
    cell_daily_cap: int = 50
    new_contributors_per_hour: float = 360.0
    new_contributor_burst: int = 60

    def __post_init__(self):
        if (self.per_hour <= 0 or self.burst < 1 or self.cell_daily_cap < 1
                or self.new_contributors_per_hour <= 0 or self.new_contributor_burst < 1):
            raise ValueError("rate limits must be positive")


class TokenBucket:
    def __init__(self, per_hour: float, burst: int, max_keys: int = 10_000, clock=time.monotonic):
        self.rate = per_hour / 3600.0
        self.burst = float(burst)
        self.max_keys = max_keys
        self.clock = clock
        self._state: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._lock = threading.Lock()

    def take(self, key: str) -> tuple[bool, int]:
        """Consume one token. Returns (allowed, retry_after_seconds)."""
        now = self.clock()
        with self._lock:
            tokens, last = self._state.pop(key, (self.burst, now))
            elapsed = max(0.0, now - last)  # a clock that goes backwards never mints tokens
            last = max(last, now)
            tokens = min(self.burst, tokens + elapsed * self.rate)
            if tokens >= 1.0:
                self._state[key] = (tokens - 1.0, last)
                allowed, retry = True, 0
            else:
                self._state[key] = (tokens, last)
                allowed, retry = False, max(1, int((1.0 - tokens) / self.rate + 0.999))
            while len(self._state) > self.max_keys:
                self._state.popitem(last=False)  # forget the least recently seen key
        return allowed, retry
