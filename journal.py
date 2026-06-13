"""Append-only JSONL journal: every decision, trade, and rejection
gets logged so you can review what the agent did and why."""

import json
from datetime import datetime, timezone
from pathlib import Path


class Journal:
    def __init__(self, cfg):
        self.path = Path("journal.jsonl")

    def _write(self, kind: str, data: dict):
        entry = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, **data}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def record_tick(self, ts, account, decision):
        self._write("tick", {"account": account, "decision": decision})

    def record_trade(self, order, result, reasoning):
        self._write("trade", {"order": order, "result": result, "reasoning": reasoning})

    def record_rejection(self, order, reason):
        self._write("rejected", {"order": order, "reason": reason})

    def record_event(self, name, data):
        self._write(name, {"data": data})
