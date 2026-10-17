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
