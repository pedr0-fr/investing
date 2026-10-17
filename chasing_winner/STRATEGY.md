# Chasing the Winner

> Each January, buy the single best-performing stock of the **prior** calendar
> year, hold it all year, then rotate into the new winner. Repeat forever.

Source idea: [@gurgavin thread](https://x.com/gurgavin/status/2109399629431488571).
This document is our working spec — we refine it here as we test.

---

## 1. The base rule (as pitched)

1. On the first trading day of year *Y*, identify the stock with the highest
   total return during year *Y−1*.
2. Put 100% of capital into that stock.
3. Hold until the first trading day of year *Y+1*.
4. Rotate into the new prior-year winner. Repeat.

**Reported backtest (as claimed in the thread):**

| Window | S&P 500 | Chasing the Winner |
|---|---|---|
| 2012 → 2026 (15 yr, $100 start) | $800 | **$176,114** |
| 1997 → 2026 (30 yr, $100 start), no stop | $1,752 | $89,418 |
| 1997 → 2026 (30 yr, $100 start), 35% stop | $1,752 | **$1,514,581** |

Claimed to beat the S&P in 11 of 15 years. Example winners cited: AMD +148%
(2019), NVDA +171% (2024), PLTR +135% (2025), SNDK +566% (2026).
Current signal: MRNA +663% → candidate to hold in 2027.

## 2. The known flaw

Concentration in a single momentum name produces brutal drawdowns. The thread
itself admits the unhedged version fell **~97% from 1999–2011** and took 23
years to recover. A single-stock, no-stop strategy is path-dependent and
ruinous if the winner reverts (which winners usually do).

## 3. The pitched fix — 35% stop-loss

- If the held stock closes 35% below the purchase price, sell.
- Sit in **cash** until the next January, then re-enter the new winner.

This reportedly turns the 30-year result from $89k into $1.5M by cutting the
left tail.

---

## 4. Why this needs independent validation (survivorship & selection traps)

Before refining, we must reproduce the claim honestly. The headline numbers are
exactly the kind that break under scrutiny:

- **Survivorship bias** — "best performer of the year" is only knowable if the
  universe includes names that later delisted/blew up. If the universe is
  "today's S&P 500," the result is fantasy.
- **Universe definition** — best performer *out of what?* All US equities? A
  penny stock up 4000% is the real "winner" most years. The thread implies
  large liquid names, but the rule as stated doesn't say.
- **Look-ahead** — index membership and "the winner" must be computed only from
  data available on the rebalance date.
- **Transaction costs, slippage, taxes** — annual rotation into a single
  volatile name is a worst case for short-term capital gains tax.
- **Single path** — one 30-year sequence is one sample. We need the
  distribution, not the anecdote.

## 5. Refinement roadmap

Phases, each gated on reproducing the prior one honestly:

- [x] **P0 — Data + engine.** Universe builder (`build_universe.py`, ~7k US
      symbols from the NASDAQ/NYSE/AMEX directory), resumable price downloader
      (`fetch_prices.py`, Yahoo chart API, adjusted monthly closes), and a
      parameterised backtester (`backtest.py`). ⚠️ Universe is *current*
      listings only → survivorship-biased; results are an **upper bound**.
      Next: run it and compare to the claimed numbers.
- [ ] **P1 — Robustness.** Vary the stop (25/35/45%), rebalance month,
      universe size, and start year. Report the *distribution* of CAGR and
      max-drawdown, not a single path. Add realistic costs & taxes.
- [ ] **P2 — Diversify the signal.** Top-N winners (N=3,5,10) instead of 1 to
      cut idiosyncratic risk. Equal- vs vol-weighted.
- [ ] **P3 — Smarter exits.** Trailing stop vs fixed stop; re-entry rules;
      cash vs T-bills while flat (the cash drag is real over 30 years).
- [ ] **P4 — Risk overlay.** Position sizing by volatility; market-regime
      filter (e.g. only hold when index > 200d MA).
- [ ] **P5 — Honest verdict.** Out-of-sample / walk-forward. Decide whether
      anything here survives costs and is worth paper-trading.

## 6. Open questions (need decisions before P0)

1. **Universe:** US large-cap (S&P 500)? Nasdaq-100? All listed US equities
   with a liquidity floor?
2. **"Best performer" metric:** total return incl. dividends, or price only?
3. **Data source:** what do we have access to (yfinance is free but has gaps &
   survivorship issues; Norgate/CRSP are survivorship-clean but paid)?
4. **Rebalance timing:** first trading day of January? Does the month matter?

## 7. Layout

```
chasing_winner/
├── STRATEGY.md         # this file — the living spec
├── src/
│   ├── build_universe.py   # fetch ~7k US tickers + metadata -> data/universe.csv
│   ├── fetch_prices.py     # resumable adjusted-price download -> data/prices_*.parquet
│   └── backtest.py         # run the strategy, compare vs S&P 500
├── data/               # cached prices / universe (gitignored)
└── results/            # equity curves, stats, logs (gitignored)
```

### How to run

```bash
pip install --user yfinance pandas pyarrow        # yfinance only used as a dep carrier
python chasing_winner/src/build_universe.py       # -> data/universe.csv
python chasing_winner/src/fetch_prices.py          # -> data/prices_1mo.parquet (resumable)
python chasing_winner/src/backtest.py --start 2012 --end 2026            # base + 35% stop
python chasing_winner/src/backtest.py --start 2012 --end 2026 --no-stop  # no stop
python chasing_winner/src/backtest.py --top 5 --common-only              # variants
```
