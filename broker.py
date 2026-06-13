"""Thin wrapper around Alpaca's trading API (paper by default)."""

import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

log = logging.getLogger("trader.broker")


class Broker:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = TradingClient(cfg.alpaca_key, cfg.alpaca_secret, paper=cfg.paper)

    # ------------------------------------------------------------------ #
    def market_is_open(self) -> bool:
        return bool(self.client.get_clock().is_open)

    def account_snapshot(self) -> dict:
        a = self.client.get_account()
        return {
            "equity": float(a.equity),
            "last_equity": float(a.last_equity),
            "cash": float(a.cash),
            "buying_power": float(a.buying_power),
        }

    def positions(self) -> list[dict]:
        return [
            {
                "symbol": p.symbol,
                "qty": int(float(p.qty)),
                "avg_entry": float(p.avg_entry_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
            }
            for p in self.client.get_all_positions()
        ]

    # ------------------------------------------------------------------ #
    def submit(self, order: dict) -> dict:
        side = OrderSide.BUY if order["side"] == "buy" else OrderSide.SELL

        if order.get("type") == "limit" and order.get("limit_price"):
            req = LimitOrderRequest(
                symbol=order["symbol"],
                qty=order["qty"],
                side=side,
                limit_price=round(float(order["limit_price"]), 2),
                time_in_force=TimeInForce.DAY,
            )
        else:
            req = MarketOrderRequest(
                symbol=order["symbol"],
                qty=order["qty"],
                side=side,
                time_in_force=TimeInForce.DAY,
            )

        result = self.client.submit_order(req)
        log.info("Submitted %s %s x%s -> id=%s", order["side"], order["symbol"], order["qty"], result.id)
        return {"id": str(result.id), "status": str(result.status)}

    def flatten_all(self):
        self.client.cancel_orders()
        self.client.close_all_positions(cancel_orders=True)
