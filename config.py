"""Configuration. Paper trading is the default and live mode must be
explicitly enabled with LIVE_TRADING=I_UNDERSTAND_THE_RISKS."""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _watchlist() -> list[str]:
    raw = os.getenv("WATCHLIST", "SPY,QQQ,AAPL,MSFT,NVDA")
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


@dataclass
class Config:
    # --- Brokerage (Alpaca) ---
    alpaca_key: str = os.getenv("ALPACA_API_KEY", "")
    alpaca_secret: str = os.getenv("ALPACA_SECRET_KEY", "")
    paper: bool = os.getenv("LIVE_TRADING", "") != "I_UNDERSTAND_THE_RISKS"

    # --- Claude ---
    anthropic_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    model: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    # --- Strategy / loop ---
    watchlist: list[str] = field(default_factory=_watchlist)
    loop_seconds: int = int(os.getenv("LOOP_SECONDS", "300"))   # 5 min
    halt_seconds: int = int(os.getenv("HALT_SECONDS", "3600"))  # 1 hr after halt

    # --- Risk limits ---
    max_position_pct: float = float(os.getenv("MAX_POSITION_PCT", "0.10"))   # 10% of equity per position
    max_order_notional: float = float(os.getenv("MAX_ORDER_NOTIONAL", "1000"))
    max_daily_loss_pct: float = float(os.getenv("MAX_DAILY_LOSS_PCT", "0.02"))  # 2% daily stop
    max_open_positions: int = int(os.getenv("MAX_OPEN_POSITIONS", "5"))

    @property
    def alpaca_base_url(self) -> str:
        return ("https://paper-api.alpaca.markets" if self.paper
                else "https://api.alpaca.markets")

    def validate(self):
        missing = []
        if not self.alpaca_key:
            missing.append("ALPACA_API_KEY")
        if not self.alpaca_secret:
            missing.append("ALPACA_SECRET_KEY")
        if not self.anthropic_key:
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise SystemExit(f"Missing env vars: {', '.join(missing)} (see .env.example)")
