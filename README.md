# AI Agentic Day Trader

An autonomous intraday trading agent. Claude acts as the decision engine; a deterministic risk manager gates every order; Alpaca executes (paper trading by default).

> **Disclaimer:** This is experimental software, not financial advice. Day trading carries substantial risk of loss. Run it in paper mode. If you ever enable live mode, you accept full responsibility for the results.

## Architecture

```
loop (every 5 min while market is open)
  ├─ market_data.py   → quotes + 15m bars for the watchlist
  ├─ analyst.py       → Claude returns strict-JSON orders + reasoning
  ├─ risk.py          → deterministic gate (Claude proposes, code disposes)
  ├─ broker.py        → Alpaca order execution (paper by default)
  └─ journal.py       → JSONL log of every decision, trade, rejection
```

Safety properties:
- **Paper trading by default.** Live mode requires `LIVE_TRADING=I_UNDERSTAND_THE_RISKS` in `.env`.
- **Long-only, cash-only.** No shorting, no margin.
- **Hard limits** on per-order notional, position size, open position count.
- **Daily circuit breaker:** if equity drops 2% from the prior close, the agent flattens everything and stands down for an hour.
- **The LLM never has the last word.** Every order passes the risk manager regardless of Claude's output.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your keys
python main.py
```

You need:
1. A free [Alpaca](https://alpaca.markets) account — use the **paper trading** API keys.
2. An [Anthropic API key](https://console.anthropic.com).

## Reviewing what it did

Everything is logged to `journal.jsonl` — one JSON object per line with the decision, Claude's reasoning, and the outcome. Pipe it into anything:

```bash
cat journal.jsonl | python -m json.tool --json-lines
```

## Tuning

All knobs live in `.env` (see `.env.example`): watchlist, loop interval, position sizing, daily loss limit. Strategy behavior lives in the system prompt in `trader/analyst.py` — edit it to change the agent's style (momentum, mean reversion, more/less active, etc.).
