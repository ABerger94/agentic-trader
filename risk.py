"""Deterministic risk gate. Claude proposes, this code disposes.

Every order must pass these checks regardless of what the model says.
Never trust the LLM to enforce its own limits.
"""

import logging
from dataclasses import dataclass

log = logging.getLogger("trader.risk")


@dataclass
class Verdict:
    approved: bool
    reason: str = ""


class RiskManager:
    def __init__(self, cfg):
        self.cfg = cfg

    # ------------------------------------------------------------------ #
    def daily_loss_breached(self, account: dict) -> bool:
        equity = account["equity"]
        last_equity = account["last_equity"]  # equity at previous close
        if last_equity <= 0:
            return False
        daily_pnl_pct = (equity - last_equity) / last_equity
        return daily_pnl_pct <= -self.cfg.max_daily_loss_pct

    # ------------------------------------------------------------------ #
    def evaluate(self, order: dict, account: dict, positions: list) -> Verdict:
        side = order.get("side")
        symbol = order.get("symbol", "").upper()
        qty = order.get("qty", 0)

        if side not in ("buy", "sell"):
            return Verdict(False, f"invalid side: {side}")
        if not symbol or not isinstance(qty, int) or qty <= 0:
            return Verdict(False, "invalid symbol or qty")
        if symbol not in self.cfg.watchlist:
            return Verdict(False, f"{symbol} not in watchlist")

        held = {p["symbol"]: p for p in positions}

        # Selling: only allow reducing/closing an existing long
        if side == "sell":
            pos = held.get(symbol)
            if not pos:
                return Verdict(False, "no position to sell (shorting disabled)")
            if qty > pos["qty"]:
                return Verdict(False, f"sell qty {qty} exceeds held {pos['qty']}")
            return Verdict(True)

        # Buying checks
        price = order.get("limit_price") or order.get("est_price") or 0
        if price <= 0:
            return Verdict(False, "buy orders require a limit_price")

        notional = price * qty
        if notional > self.cfg.max_order_notional:
            return Verdict(False, f"notional ${notional:,.0f} > max ${self.cfg.max_order_notional:,.0f}")

        equity = account["equity"]
        existing = held.get(symbol, {"market_value": 0})["market_value"]
        if (existing + notional) > equity * self.cfg.max_position_pct:
            return Verdict(False, "would exceed max position % of equity")

        if symbol not in held and len(held) >= self.cfg.max_open_positions:
            return Verdict(False, "max open positions reached")

        if notional > account["cash"]:
            return Verdict(False, "insufficient cash (no margin allowed)")

        return Verdict(True)
