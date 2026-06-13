"""
Core agent loop: observe -> analyze -> decide -> act -> journal.

The agent wakes on an interval, pulls market data for its watchlist,
asks Claude for a structured trading decision, runs it through the
risk manager, and (if approved) executes via the broker.
"""

import json
import time
import logging
from datetime import datetime, timezone

from .config import Config
from .market_data import MarketData
from .analyst import ClaudeAnalyst
from .risk import RiskManager
from .broker import Broker
from .journal import Journal

log = logging.getLogger("trader.agent")


class TradingAgent:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.broker = Broker(cfg)
        self.market = MarketData(cfg)
        self.analyst = ClaudeAnalyst(cfg)
        self.risk = RiskManager(cfg)
        self.journal = Journal(cfg)

    # ------------------------------------------------------------------ #
    def run(self):
        log.info("Agent starting | mode=%s | watchlist=%s",
                 "PAPER" if self.cfg.paper else "LIVE", self.cfg.watchlist)
        while True:
            try:
                self.tick()
            except KeyboardInterrupt:
                log.info("Shutting down.")
                break
            except Exception:
                log.exception("Tick failed; sleeping and retrying.")
            time.sleep(self.cfg.loop_seconds)

    # ------------------------------------------------------------------ #
    def tick(self):
        if not self.broker.market_is_open():
            log.info("Market closed. Sleeping.")
            return

        account = self.broker.account_snapshot()

        # Hard stop: daily loss limit reached -> flatten and stand down
        if self.risk.daily_loss_breached(account):
            log.warning("Daily loss limit breached. Flattening all positions.")
            self.broker.flatten_all()
            self.journal.record_event("daily_loss_halt", account)
            time.sleep(self.cfg.halt_seconds)
            return

        snapshot = self.market.snapshot(self.cfg.watchlist)
        positions = self.broker.positions()

        decision = self.analyst.decide(
            snapshot=snapshot,
            positions=positions,
            account=account,
        )
        log.info("Claude decision: %s", json.dumps(decision, default=str))

        for order in decision.get("orders", []):
            verdict = self.risk.evaluate(order, account, positions)
            if not verdict.approved:
                log.info("Risk REJECTED %s: %s", order, verdict.reason)
                self.journal.record_rejection(order, verdict.reason)
                continue

            result = self.broker.submit(order)
            self.journal.record_trade(order, result, decision.get("reasoning", ""))

        self.journal.record_tick(
            ts=datetime.now(timezone.utc).isoformat(),
            account=account,
            decision=decision,
        )
