# P0 Findings — can we reproduce the $176k claim?

**Short answer: no.** With an honest(-ish) point-in-time universe, the strategy
*as literally stated* ("buy THE single best performer of last year") is a
wealth destroyer. The thread's headline number is a selection/narrative
artifact. The configurations that *do* beat the market only do so by leaning on
survivorship + look-ahead bias — i.e. they aren't deployable.

Data: monthly adjusted closes for 6,581 US tickers (NASDAQ/NYSE/AMEX), 1962–2026,
via Yahoo. **Universe = current listings only → survivorship-biased (an upper
bound).** Benchmark: S&P 500 total level. $100 start.

## Result grid (2012–2026, 15 yr)

| Universe | Top-N | Stop | Final $ | CAGR | maxDD | Trust |
|---|---|---|---|---|---|---|
| All US equities | 1 | 35% | **$1** | −27% | −100% | honest |
| All US equities | 1 | none | **$0** | −59% | −100% | honest |
| ≥$10B cap¹ | 1 | 35% | $18 | −13% | −92% | biased¹ |
| ≥$10B cap¹ | 1 | none | $52 | −6% | −89% | biased¹ |
| ≥$10B cap¹ | 3 | 35% | $1,658 | 18% | −54% | biased¹ |
| ≥$10B cap¹ | 5 | 35% | $10,047 | 33% | −5% | biased¹ |
| ≥$10B cap¹ | 10 | 35% | $6,022 | 28% | −11% | biased¹ |
| ≥$50B cap¹ | 1 | 35% | $15,045 | 39% | −37% | biased¹ |
| ≥$50B cap¹ | 5 | none | $29,251 | 42% | −5% | biased¹ |
| **S&P 500 (benchmark)** | — | — | **$561** | **11.4%** | **−9%** | — |

30-year (1997–2026), ≥$10B, top-1, 35% stop → **$1, −98% maxDD** (S&P → $969).

¹ The market-cap filter uses *today's* market cap. A 2012 pick only clears a
$10B/$50B bar because it survived and grew into it — so these rows bake in
look-ahead + survivorship. They are **not** a tradeable result; they show what
you'd get if you'd magically known in advance which names would become giants.

## What this tells us

1. **The literal rule picks pump-and-dumps.** The true best performer in the
   whole US market each year is a micro-cap up 1,000–130,000% (PPCB +134,050%
   in 2025) that then collapses. $100 → $1. The thread's cited winners (AMD,
   NVDA, PLTR) were *never* the actual best performers of their prior year —
   they're a hand-picked mega-cap narrative.
2. **Single-name concentration is the core flaw, not the fix.** Every top-1
   variant has an ~90–100% max drawdown. The 35% stop softens but does not save
   it — a 35% stop still compounds losses when you re-enter a *new* reverting
   winner every January. Over a full cycle (30 yr) top-1 → total loss.
3. **The only thing that "works" is diversification + big-cap momentum** (top-5
   large-cap), and even that is inflated here by survivorship/look-ahead. That's
   not "chasing the winner" — it's "own a basket of established momentum
   leaders," which is just a tilt on the market.

## Verdict

The pitched strategy does not survive honest reproduction. The refinement that
*might* have legs — and is worth testing properly — is **top-N (5–10),
large-cap, momentum basket with a trailing stop**, evaluated on a
**survivorship-clean, point-in-time universe**. Everything else is a mirage.

## Next (P1) — make the "maybe real" version honest

- [ ] Replace the current-mktcap proxy with **point-in-time** membership
      (historical S&P 500 / Russell 1000 constituents) — this is the single
      biggest fix and needs survivorship-clean data (Norgate/CRSP/Polygon).
- [ ] Add delisted names so the left tail is real.
- [ ] Transaction costs, slippage, and short-term-capital-gains tax on the
      annual rotation (brutal for this strategy).
- [ ] Report the *distribution* over many start years, not one path.
- [ ] Trailing vs fixed stop; T-bill yield while in cash.

Run anything in the grid with:
`python src/backtest.py --start 2012 --end 2026 --top 5 --stop 35 --min-mktcap 10 --common-only`

---

# P1 Findings — overlapping mid-cap momentum basket

Construction (`src/momentum_basket.py`): universe = common stocks in a
**$5–50B market-cap band**, **N equal-capital slots**, **no stop**, each slot
held `hold` months, rotations **staggered** (one slot comes due every
`hold/N` months — rotate one name at a time). Signal = trailing
`signal-lookback`-month return. Same survivorship/look-ahead caveat: the cap
band uses *current* market cap.

| Config | Final $ | CAGR | maxDD | vs S&P |
|---|---|---|---|---|
| **n=6, hold=12, sig=12 (spec'd)** | **$566** | 12.4% | **−65%** | loses ($583, −25%) |
| n=6, hold=6 | $366 | 9.1% | −59% | loses |
| n=6, hold=18 | $1,663 | 20.9% | −59% | wins return, 2.4× DD |
| n=10, hold=12 | $896 | 15.9% | −62% | wins return, worse DD |
| n=6, hold=12, sig=6 | $2,408 | 23.9% | −78% | wins return, 3× DD |
| **n=6, hold=12 (30 yr, 1997–2026)** | **$3,924** | 13.1% | **−73%** | wins ($973, 7.9%) |
| S&P 500 (2012–2026) | $583 | 12.6% | −25% | — |

### Read

- The **exact spec'd config underperforms** the index on *both* return and
  risk. Staggered rotation smooths turnover but doesn't create edge.
- Configs that beat the S&P on absolute return (hold=18, short signal, 30-yr)
  all pay for it with **−60% to −78% drawdowns** — roughly 2.5–3× the market.
  That's not alpha, it's leverage-via-volatility on a mid-cap momentum factor.
- The 30-yr outperformance ($3.9k vs $0.97k) is the most interesting result,
  but it is still inflated by the current-mktcap selection — a $5–50B *today*
  name had to survive to be in the band at all.

### Verdict (unchanged direction)

Mid-cap momentum has a real factor behind it, but as built here it's a
higher-octane S&P, not a free lunch — and the drawdowns would be hard to hold
through live. Before trusting any of it we still need a **point-in-time,
survivorship-clean universe** and **costs/taxes** (88–178 rotations over the
window is meaningful turnover). That remains the gate on a real verdict.

Run with:
`python src/momentum_basket.py --n 6 --hold 12 --mktcap-min 5 --mktcap-max 50 --start 2012 --end 2026`
