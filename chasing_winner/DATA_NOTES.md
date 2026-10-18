# Data sourcing notes — the survivorship problem

Goal: run the strategy on a *point-in-time, survivorship-clean* universe with
*real historical market caps*, so a ≥$20B vs ≥$40B floor comparison is honest.
Here is exactly what free data can and cannot deliver, as tested 2026-10-17.

## What we have

| Data | Source | Status | Coverage |
|---|---|---|---|
| Point-in-time S&P 500 membership | [fja05680/sp500](https://github.com/fja05680/sp500) | ✅ have it | daily, 1996-01 → 2026-08, **incl. delisted** |
| Prices (adjusted) for *current* listings | Yahoo chart API | ✅ have it | 6,581 tickers, monthly |
| Historical shares outstanding → market cap | SEC EDGAR XBRL (`companyconcept`) | ✅ reachable | **2009+ only** (XBRL era) |

Membership files saved to `data/sp500_membership_daily.csv` and
`data/sp500_ticker_start_end.csv`. 1,209 unique tickers were in the S&P 500 at
some point since 1996; **503 are current members, 759 have since left.**

## What we CANNOT get for free

- **Prices for delisted / acquired members.** This is the blocker. Of the 1,209
  ever-members, **510 (42%) are absent from our price panel** — they delisted,
  went bankrupt, or were acquired. Tested recovery:
  - Yahoo chart API → **HTTP 404** for every old symbol (AGN, AET, XLNX, CELG,
    TWX, RTN, LEH, ENE, WAMUQ, ABC, …). Yahoo drops delisted symbols.
  - Stooq → Cloudflare/JS bot-wall, no CSV.
  - So the left tail (the companies that *failed*) is missing. Any backtest on
    the names we do have is **survivorship-biased upward** — we only keep the
    survivors.
- **Historical market caps before 2009.** No free XBRL; FMP's
  `historical-market-capitalization` needs a paid key (demo → 401).

## Consequence

A *fully* survivorship-clean, multi-decade, market-cap-floored backtest is **not
possible with free data**. The realistic honest options:

1. **SEC caps, 2010–2026 (free).** Universe = point-in-time S&P members we have
   prices for; real historical caps from SEC → apply ≥$20B / ≥$40B floors
   point-in-time. 16-year window. Residual survivorship bias (missing failed
   names), but far better than today's-cap: post-2010 S&P exits are mostly
   acquisitions (end at a takeout price, not zero), so the bias is milder.
2. **Point-in-time membership, 1996–2026 (free).** Use S&P membership as the
   large-cap universe (no explicit $ floor). Longer window, still missing the
   delisted-price tail.
3. **Paid, survivorship-clean (Sharadar/Norgate/CRSP/Polygon).** The only fully
   rigorous path — real prices for delisted names + historical caps.

Option 1 is the best free way to actually answer "≥$20B vs ≥$40B — which floor
wins," with the bias documented and bounded. Recorded here so the choice and its
caveats are explicit.

## Price panels available (as of 2026-10-17)

| file | interval | tickers | span | notes |
|---|---|---|---|---|
| `data/prices_1mo.parquet` | monthly | 6,315 | 1970 → 2026-09-21 | month-END closes; older cutoff |
| `data/prices_1wk.parquet` | weekly | 6,633 | 1970 → 2026-10-16 | 7-day bars, current, 0% sparse |

Both fetched via `fetch_prices.py` (explicit `period1/period2`, no range=max
downsampling). Weekly enables finer rebalance-timing, tighter stops, and
shorter lookbacks than month-end data allows. Validate with `validate_prices.py`.

## International large-cap panel (added 2026-10-18)

| file | interval | tickers | span | notes |
|---|---|---|---|---|
| `data/universe_intl.csv` | — | 1,288 | — | ≥$10B, 44 countries (ex-US), from companiesmarketcap.com |
| `data/prices_intl_1wk.parquet` | weekly | 1,267 | 1970 → 2026-10-18 | 98% coverage, 100% clean |

Source: companiesmarketcap.com per-country pages (free, no key) give
Yahoo-ready tickers + market cap (USD) + country. Prices via the same chart-API
fetcher. Build: `build_intl_universe.py` then `fetch_intl_prices.py --interval 1wk`.
Known gap: UAE (~.AE tickers) — Yahoo uses different suffixes for Gulf exchanges.
No sector/industry from this source. US large-caps are in the separate US panel.
