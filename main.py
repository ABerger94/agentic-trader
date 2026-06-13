import logging

from trader.config import Config
from trader.agent import TradingAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

if __name__ == "__main__":
    cfg = Config()
    cfg.validate()
    if not cfg.paper:
        print("\n*** LIVE TRADING ENABLED — REAL MONEY AT RISK ***\n")
    TradingAgent(cfg).run()
