"""Server-side cost recomputation from a versioned price table.

The server never trusts or overwrites the client's ``usage.cost_usd_client``.
It computes its own value from the record's token counts and a price table
(``data/prices.json``: source URL, as-of date, retrieval note) and stores it in
the separate ``server_costs`` table together with the table id, or a reason
why no value could be computed.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DEFAULT_PRICES = DATA_DIR / "prices.json"
TOKEN_FIELDS = (("input_tokens", "input"), ("output_tokens", "output"),
                ("cache_write_tokens", "cache_write"), ("cache_read_tokens", "cache_read"))
REQUIRED_SOURCE = ("name", "url", "as_of", "retrieved_at", "retrieved_via", "verified_live")


@dataclass(frozen=True)
class CostResult:
    cost_usd: float | None
    price_table_id: str
    reason: str  # "ok" | "route_not_covered" | "model_not_in_table" | "tokens_missing"


class PriceTable:
    def __init__(self, data: dict, sha256: str | None = None):
        for key in ("price_table_id", "currency", "unit", "source", "applies_to_routes", "models"):
            if key not in data:
                raise ValueError(f"price table is missing {key!r}")
        missing = [k for k in REQUIRED_SOURCE if k not in data["source"]]
        if missing:
            raise ValueError(f"price table source is missing {missing}")
        if data["unit"] != "per_million_tokens" or data["currency"] != "USD":
            raise ValueError("only USD per_million_tokens tables are supported")
        for entry in data["models"]:
            for _, price_key in TOKEN_FIELDS:
                value = entry[price_key]
                if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"bad price {price_key} for {entry.get('model')}")
        self.data = data
        self.id = data["price_table_id"]
        self.sha256 = sha256
        self.routes = set(data["applies_to_routes"])
        # Longest id first so "claude-opus-5-5" wins over "claude-opus-5".
        self._entries = sorted(data["models"], key=lambda e: len(e["model"]), reverse=True)

    @classmethod
    def load(cls, path: Path = DEFAULT_PRICES) -> "PriceTable":
        raw = Path(path).read_bytes()
        return cls(json.loads(raw), hashlib.sha256(raw).hexdigest())

    def lookup(self, model_id: str) -> dict | None:
        for entry in self._entries:
            m = entry["model"]
            if model_id == m or any(model_id.startswith(m + sep) for sep in ("-", "@", "[")):
                return entry
        return None

    def cost(self, record: dict) -> CostResult:
        if record["model"].get("route") not in self.routes:
            return CostResult(None, self.id, "route_not_covered")
        entry = self.lookup(record["model"]["id"])
        if entry is None:
            return CostResult(None, self.id, "model_not_in_table")
        usage = record["usage"]
        if any(usage.get(tok) is None for tok, _ in TOKEN_FIELDS):
            return CostResult(None, self.id, "tokens_missing")
        total = sum(usage[tok] * entry[price] for tok, price in TOKEN_FIELDS) / 1_000_000
        return CostResult(round(total, 6), self.id, "ok")

    def describe(self) -> dict:
        return {"price_table_id": self.id, "sha256": self.sha256, "source": self.data["source"],
                "applies_to_routes": sorted(self.routes), "notes": self.data.get("notes", [])}
