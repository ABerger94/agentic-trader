"""Market data via Alpaca's data API: latest quotes plus recent bars
so Claude has intraday context (trend, range, volume)."""

import logging
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

log = logging.getLogger("trader.market")


class MarketData:
    def __init__(self, cfg):
        self.client = StockHistoricalDataClient(cfg.alpaca_key, cfg.alpaca_secret)

    def snapshot(self, symbols: list[str]) -> dict:
        out: dict[str, dict] = {}

        quotes = self.client.get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=symbols)
        )

        bars = self.client.get_stock_bars(
            StockBarsRequest(
                symbol_or_symbols=symbols,
                timeframe=TimeFrame(15, TimeFrameUnit.Minute),
                limit=20,
            )
        )

        for sym in symbols:
            q = quotes.get(sym)
            sym_bars = bars.data.get(sym, [])
            out[sym] = {
                "bid": float(q.bid_price) if q else None,
                "ask": float(q.ask_price) if q else None,
                "bars_15m": [
                    {
                        "t": b.timestamp.isoformat(),
                        "o": float(b.open),
                        "h": float(b.high),
                        "l": float(b.low),
                        "c": float(b.close),
                        "v": float(b.volume),
                    }
                    for b in sym_bars
                ],
            }
        return out
