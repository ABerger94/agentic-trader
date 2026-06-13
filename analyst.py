"""Claude as the decision engine. Sends market snapshot + portfolio
state, gets back strict JSON: a list of orders plus reasoning.

Claude is told what it may NOT do (exceed limits, use leverage,
short) so the model and the risk manager enforce the same rules.
"""

import json
import logging
import anthropic

log = logging.getLogger("trader.analyst")

SYSTEM_PROMPT = """You are the decision engine for an automated intraday equity trader.

You will receive:
- market: latest quotes and recent 15-minute bars per symbol
- positions: current open positions
- account: equity, cash, buying power, today's P&L

Respond with ONLY a JSON object, no markdown fences, in this schema:
{
  "reasoning": "brief explanation of your read on the market",
  "orders": [
    {"symbol": "AAPL", "side": "buy"|"sell", "qty": <int>, "type": "market"|"limit", "limit_price": <float|null>}
  ]
}

Rules you must follow:
- "orders" may be empty. Doing nothing is often correct.
- Long-only. Never short. "sell" only to reduce/close an existing position.
- Stay within the risk limits provided in the user message.
- Prefer limit orders near the current quote over market orders.
- Do not churn: if your last decision was recent and nothing changed, return no orders.
"""


class ClaudeAnalyst:
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = anthropic.Anthropic(api_key=cfg.anthropic_key)

    def decide(self, snapshot: dict, positions: list, account: dict) -> dict:
        payload = {
            "market": snapshot,
            "positions": positions,
            "account": account,
            "risk_limits": {
                "max_position_pct_of_equity": self.cfg.max_position_pct,
                "max_order_notional_usd": self.cfg.max_order_notional,
                "max_open_positions": self.cfg.max_open_positions,
            },
        }

        msg = self.client.messages.create(
            model=self.cfg.model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
        )

        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            decision = json.loads(text)
        except json.JSONDecodeError:
            log.error("Claude returned non-JSON, treating as no-op: %s", text[:300])
            return {"reasoning": "parse_error", "orders": []}

        if not isinstance(decision.get("orders"), list):
            decision["orders"] = []
        return decision
