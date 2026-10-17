> ⚠️ **DATA-QUALITY CORRECTION (supersedes earlier numbers).** The first price
> pull used Yahoo `range=max`, which silently downsampled 288 long-history S&P
> members (AAPL, AMD, NVDA, Devon…) to **quarterly** — no December close — so
> they were mis-ranked or dropped. A second bug applied a $5 floor to
> *split-adjusted* prices, wrongly excluding split-heavy winners (NVDA's adj
> 2016 price ≈ $0.27). Both are fixed (explicit `period1/period2`;
> `validate_prices.py` gate; no $-floor for S&P members). **Clean-data results
> are in the P3′/P4′ sections and are higher than the stale tables below** — the
> bug had *understated* the strategy. Qualitative conclusions (concentration
> risk, start-date dependence, the all-equities $176k being a micro-cap mirage)
> are unchanged.

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

---

# P1b — market-cap FLOOR x basket size sweep

`src/sweep_mktcap.py`: 3 floors (≥5/20/50B, **no upper bound**) x basket sizes
1–6 = 18 strategies. Hold 12 mo, no stop, 12-mo signal, 2012–2026, $100 start.

| floor | n | universe | final $ | CAGR % | maxDD % | rot |
|---|---|---|---|---|---|---|
| ≥$5B | 1 | 1246 | $60 | -3.4 | -95 | 14 |
| ≥$5B | 2 | 1246 | $1,246 | 18.5 | -85 | 29 |
| ≥$5B | 3 | 1246 | $1,793 | 21.5 | -73 | 44 |
| ≥$5B | 4 | 1246 | $29,609 | 46.8 | -67 | 58 |
| ≥$5B | 5 | 1246 | $1,354 | 19.2 | -69 | 74 |
| ≥$5B | 6 | 1246 | $1,140 | 17.8 | -60 | 88 |
| ≥$20B | 1 | 540 | $4,724 | 29.7 | -78 | 14 |
| ≥$20B | 2 | 540 | $7,442 | 33.7 | -64 | 29 |
| ≥$20B | 3 | 540 | $11,519 | 37.7 | -51 | 44 |
| ≥$20B | 4 | 540 | $19,203 | 42.5 | -52 | 58 |
| ≥$20B | 5 | 540 | $16,889 | 41.3 | -47 | 74 |
| ≥$20B | 6 | 540 | $13,395 | 39.1 | -34 | 88 |
| ≥$50B | 1 | 291 | $32,720 | 47.8 | -34 | 14 |
| ≥$50B | 2 | 291 | $29,570 | 46.7 | -59 | 29 |
| ≥$50B | 3 | 291 | $56,220 | 53.2 | -47 | 44 |
| ≥$50B | 4 | 291 | $20,981 | 43.4 | -47 | 58 |
| ≥$50B | 5 | 291 | $23,993 | 44.7 | -46 | 74 |
| ≥$50B | 6 | 291 | $21,251 | 43.5 | -40 | 88 |
| **S&P 500** | - | - | **$583** | **12.6** | **-25** | - |

**Read it skeptically.** The dominant pattern — *higher floor → higher return*
— is almost entirely the **bias getting worse, not the strategy getting
better**: a stock only clears a ≥$50B floor *today* because it already grew
into a mega-cap, so the ≥$50B universe (291 names) is a hand-picked basket of
known survivors. The ≥$5B n=1 = $60 (−95% DD) is the least-biased cell and it
*loses to cash*. The jumpy single cells (≥$5B n=4 = $29k) are single-name luck,
not signal. Nothing here changes the P1 verdict: needs a point-in-time universe
before any number is believable.

Run with: `python src/sweep_mktcap.py --start 2012 --end 2026 --hold 12`

---

# P2 Findings — HONEST data: point-in-time membership + real caps

This is the result that matters. We removed the "today's-cap" look-ahead two
ways (see `DATA_NOTES.md` for sourcing). Engine: `src/engine.py` (time-varying
eligibility). Residual caveat throughout: ~42% of ever-S&P-members delisted and
their prices aren't free, so even these numbers still **flatter** the strategy
(the missing names are the failures).

## Part A — point-in-time S&P 500 membership universe (1997–2026, no $ floor)

`src/run_membership.py` — eligible = actual S&P members that month.

| basket n | final $ | CAGR % | maxDD % |
|---|---|---|---|
| 3 | $117 | 0.5 | −96 |
| 4 | $1,957 | 10.5 | −95 |
| 5 | $580 | 6.1 | −84 |
| 6 | $526 | 5.7 | −76 |
| **S&P 500** | **$973** | **7.9** | **−53** |

n=3 and n=5/6 lose to the index; the n=4 "win" is a single lucky slot (its
neighbours lose), not a real effect. Drawdowns are −76% to −96%.

## Part B — real cap floors ≥$20B vs ≥$40B (SEC shares × price, 2010–2026)

`src/run_floors.py` — eligible = S&P member that month AND real market cap ≥ floor.

| floor | basket n | final $ | CAGR % | maxDD % |
|---|---|---|---|---|
| ≥$20B | 3 | $289 | 6.5 | −57 |
| ≥$20B | 4 | $637 | 11.6 | −49 |
| ≥$20B | 5 | $583 | 11.0 | −43 |
| ≥$20B | 6 | $408 | 8.7 | −44 |
| ≥$40B | 3 | $723 | 12.5 | −41 |
| ≥$40B | 4 | $373 | 8.1 | −36 |
| ≥$40B | 5 | $280 | 6.3 | −44 |
| ≥$40B | 6 | $437 | 9.2 | −32 |
| **S&P 500** | - | **$713** | **12.4** | **−25** |

### Which floor is best? — Neither wins.

- **No configuration reliably beats buy-and-hold S&P 500.** The best cells
  (≥$40B n=3: $723; ≥$20B n=4: $637) merely *match* the index's $713 while
  carrying **1.5–2.3× the drawdown** (−41% to −49% vs −25%).
- **The floor is not a real lever.** ≥$20B peaks at n=4, ≥$40B peaks at n=3 —
  they flip, and average outcomes are near-identical ($20B ≈ $479, $40B ≈ $453).
  That inconsistency is the signature of noise, not edge. The only robust effect
  of a higher floor is slightly *lower drawdown* (more mega-cap = less
  volatile), bought with no extra return.
- **And this still overstates the strategy** — the missing delisted names would
  only drag it down further.

## Bottom line

The entire apparent edge of "Chasing the Winner" / mid-cap momentum rotation in
the earlier runs ($10k–$56k) was an artifact of selecting on *today's* market
cap, i.e. picking names we already know became giants. On point-in-time data
with real caps, the strategy **matches the market at best and roughly doubles
the drawdown** — it does not beat simply holding the S&P 500. The thread's
$176k claim does not survive honest reproduction.

Reproduce: `python src/run_membership.py` and `python src/run_floors.py`

---

# P3 — does the ORIGINAL single-winner rule replicate? (yes, but it's a start-date illusion)

The thread's actual rule: each January buy the **single** best-performing S&P 500
stock of the prior year, hold one year. Run on point-in-time membership
(`run_membership.py --sizes 1`), n=1:

| Start → 2026 | final $100 → | CAGR | maxDD | S&P | worst year |
|---|---|---|---|---|---|
| **2012** | **$2,520** | 24.3% | −46% | $583 | — |
| 2007 | $605 | 9.5% | −85% | $532 | 2008: −60% |
| **2000** | **$80** | −0.8% | **−97%** | $549 | 2001: −83% |

The 2012-start picks are real and recognisable — BIIB, EXPE, NFLX, AMZN, ALGN,
FTNT, PAYC, **TSLA (2021), FSLR, NVDA (2024), PLTR (2025)** — and they match the
thread's marquee names. So **starting in 2012 it genuinely beats the S&P ~4.3×.**

But this is **path/start-date dependent, not a durable edge:**

- Start in **2000** and the identical rule **loses money over 26 years** (−97%
  drawdown) while the S&P 5×'d — QCOM in 2000 then the dot-com unwind.
- Start in **2007** → −85% drawdown (2008 −60%), barely ties the index.
- 2012 is the single most flattering start: it begins *after* the GFC and rides
  a historic bull with no blow-up among the yearly winners. Single-stock
  concentration means one −83% (2001) or −60% (2008) year is unrecoverable.

Also: $2,520 is a big win, but it is **nowhere near the thread's $176k** — that
magnitude isn't reproducible on the S&P and almost certainly comes from an
all-equities universe (the micro-cap pumps we saw in P0) or a different method.

**Answer: yes, the 2012-onward success is real on honest S&P data — but it's a
cherry-picked regime. The same rule is a wealth-destroyer across a full cycle,
and even the good window needs you to hold a single stock through −46%.**

---

# P4 — reconciling our 25x with the chart's ~1,200x (`2012winners.jpeg`)

The chart compounds each year's S&P best-performer's **calendar-year** gain,
implicitly buying at the prior **Dec-31** close. Its printed next-year figures
compound to **~1,212x** ($100→$121k). Our mechanical run gave **25x**. The gap
is entirely **method + timing + data**, not a contradiction (`reconcile_chart.py`):

| Version | Result | What changed |
|---|---|---|
| Our Jan-rebalance, n=1 | **25x** | enters end-of-January |
| Our run w/ chart's method | **234x** | enter prior **Dec-31**, calendar-year selection |
| Chart's own figures | **1,212x** | complete data (incl. SNDK/DVN), zero friction |

> NOTE / correction: this is **not** "perfect hindsight." Buying *last year's*
> winner is knowable on Jan 1 — the picks require no look-ahead. The gap is
> entry timing + gaps in our free data + trading frictions, plus the real risk
> that it's a single-stock bet (see P3: −97% if started in 2000).

**25x → 234x = entry timing (≈9×).** Buying at Dec-31 vs one month later is
decisive on parabolic names: NVDA 2024 is **+171% Dec→Dec but only +95%** from
end-January; TSLA 2021 **+50% vs +18%**. A one-month lag roughly halves the
monster years. (Verified: our Dec→Dec returns match the chart's exactly.)

**234x → 1,212x = data/survivorship + price-vs-total-return.** With the chart's
method we still pick a different name in 6/14 years. The killer is **SNDK 2026
(+566%)** — a Feb-2025 IPO our free data can't price, so we take MU (+113%)
instead; that one swap is ~3×. Plus DVN 2022 (+40%) which our panel drops on a
data gap (we take FTNT, −32%). A few such names explain most of the residual.

**The 1,212x does NOT require foresight** — "buy last year's winner" is knowable
on Jan 1. It assumes complete data, buying at the exact prior close, and no
slippage/costs/taxes. Our 25x isn't "wrong" either — it answers the realistic
mechanical question (monthly rebalance) on survivor-biased free data with gaps.
The 50× gap between them is **entry timing + our data gaps + frictions**, not a
flaw in the strategy's logic. The genuine risk is elsewhere: it's a single-stock
bet (P3: −97% if started in 2000). Reproduce: `python src/reconcile_chart.py`

---

# CLEAN-DATA RESULTS (supersede P1b/P2/P3/P4 above)

Panel re-fetched with explicit `period1/period2` → 100% clean monthly
(6,315 tickers, verified by `validate_prices.py`). Point-in-time S&P membership,
no $-floor on adjusted prices. S&P 500 = benchmark, $100 start.

## P3′ — original single-winner rule (n=1, annual), by start year

| Start → 2026 | final $ | CAGR | maxDD | S&P | 
|---|---|---|---|---|
| **2012** | **$7,990** | 34.6% | −46% | $583 |
| 2007 | $1,207 | 13.4% | −93% | $532 |
| 2000 | $143 | 1.3% | **−99%** | $549 |

The 2012 start is now an even bigger win (~13.7× the S&P) — the quarterly bug had
hidden NVDA/AMD. But the verdict stands and is *starker*: start in **2000** and
the same rule is nearly wiped out (−99% drawdown, barely above breakeven over 26
years while the S&P 5×'d). It's a concentrated single-stock bet whose success is
regime/start-date dependent.

## P2′ — ≥$20B vs ≥$40B floor (real SEC caps, 2010–2026)

| floor | n | final $ | CAGR % | maxDD % |
|---|---|---|---|---|
| ≥$20B | 3 | $816 | 13.4 | −47 |
| ≥$20B | 4 | $1,199 | 16.0 | −49 |
| ≥$20B | **5** | **$3,330** | 23.3 | −49 |
| ≥$20B | 6 | $2,887 | 22.2 | −38 |
| ≥$40B | 3 | $1,149 | 15.7 | −34 |
| ≥$40B | 4 | $729 | 12.6 | −29 |
| ≥$40B | 5 | $2,060 | 19.8 | −54 |
| ≥$40B | 6 | $1,778 | 18.7 | −47 |
| **S&P 500** | - | **$713** | **12.4** | **−25** |

On clean data the basket **does beat buy-and-hold** over 2010–2026 (most cells >
$713) — the earlier "no edge" conclusion was partly the data bug. **Which floor
wins:** ≥$20B gives higher returns at every matched basket size (more mid/large
momentum names); ≥$40B gives lower drawdowns (more mega-cap, calmer) but less
return. Best return: **≥$20B, n=5** ($3,330, 23.3%). Best drawdown: ≥$40B, small
n. Caveats remain: −38%/−54% drawdowns (1.5–2× the index), 2010–2026 is a bull
window, and residual survivor bias (missing delisted members still flatters it).

## P4′ — reconciliation with the chart

| Version | Result |
|---|---|
| Our Jan-rebalance, n=1 (2012) | **80×** ($7,990) |
| Our run w/ chart's method (Dec-31 entry) | **536×** ($53,596), picks match **13/14** |
| Chart's own figures | **1,212×** ($121,159) |

With clean data the chart's method reproduces on our side at **536×**, matching
**13 of 14** picks (AMD, Devon, NVDA, OXY all correct now). The *entire* residual
to 1,212× is **one name — Sandisk 2026** (+566%), a Feb-2025 spinoff the chart
measures from its debut; we take WDC (+164%). So the chart is **not** a
hindsight trick: it's a real, implementable strategy. The gap vs a realistic run
is **entry timing** (Dec-31 vs January ≈ halves parabolic years) plus that one
IPO-measurement case — not fakery. The real caveat is concentration risk (P3′).

---

# P5 — DCA rotation & rebalance-timing (single-winner, 2012–2026, clean data)

> **Timing convention:** monthly bars are priced at the MONTH-END close, so an
> anchor labeled month M = **trade at the close of month M−1 (start of month M)**
> on that signal, then earn month M onward. So "January" = trade **Dec-31** (the
> chart's method, $56,763); "February" = trade **Jan-31** ($7,990); "April" =
> trade Mar-31. The Jan→Feb gap IS "trade Dec-31 vs Jan-31."

Does spreading the old→new hand-off over 3 months reduce the sensitivity to the
exact rebalance date? Tested every anchor month Jan–Dec, all-at-once vs DCA-3mo
(`src/dca_rotation.py`). CAGR is the fair comparator.

| mode | CAGR mean | CAGR range | spread | std | final $ range |
|---|---|---|---|---|---|
| all-at-once | 18.8% | −12.5 .. 53.7% | 66.2pp | 17.8 | $15 .. $56,763 |
| DCA 3-month | 18.6% | −12.8 .. 46.5% | 59.3pp | 16.6 | $14 .. $28,062 |
| S&P 500 | 12.7% | — | — | — | — |

## Conclusions

1. **Rebalance timing dominates the result.** Same rule, same window — CAGR runs
   from −12.5% (April anchor) to +53.7% (January), a ~4,000× spread in final
   wealth. January→February alone is 7× ($56,763→$7,990). This is the Dec/Jan
   effect the thread's chart benefits from, generalised: the single best month
   (Jan, buying on the Dec-31 signal) massively flatters the strategy.
2. **DCA over 3 months does NOT fix it.** Spread only narrows 66→59pp (std
   17.8→16.6). The disaster anchors (Apr/May, −95%+ drawdown) stay disasters.
3. **Why DCA can't save it:** you're still ~100% in a *single stock* ~9 months a
   year. Spreading the hand-off over a quarter blends the entry a little; it does
   nothing about one stock's fate driving the whole year.
4. **DCA's only real benefit is drawdown**, and only in the good anchors (Jan
   −44%→−33%): a gradual entry avoids catching one bad month. Modest.
5. **The fragility is concentration, not timing.** A strategy whose outcome
   swings 4,000× on the calendar month you happen to trade is not robust, and no
   rebalance schedule repairs that. The real lever is **diversification** — the
   N-stock baskets (P2′) are far more stable. And "January is best" is itself
   partly luck of this one path; don't read it as a tradeable edge.

Run: `python src/dca_rotation.py`

---

# P6 — lookback × holding-period grid (single-winner, 2012–2026, clean, phase-averaged)

Pick on a trailing L-month return, rotate every H months, L,H in 6..12. Each
cell is PHASE-AVERAGED over all start months (controls for the P5 timing luck).
`src/lookback_hold_grid.py`.

Mean CAGR % (S&P = 12.7%; baseline L12/H12 = 18.8%):

| L \ H | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|
| 6 | 21.3 | 21.2 | 21.0 | 22.2 | 20.1 | 19.2 | 17.7 |
| 7 | 22.2 | 21.9 | 23.0 | 24.9 | 21.9 | 21.1 | 20.0 |
| 8 | 27.0 | 25.3 | 27.3 | 28.2 | 24.4 | 24.8 | 22.6 |
| 9 | 28.1 | 28.5 | 28.4 | 29.7 | 25.8 | 24.2 | 23.9 |
| 10 | **33.3** | 31.3 | 33.2 | 30.2 | 26.7 | 25.1 | 23.7 |
| 11 | 30.9 | 28.9 | 27.1 | 25.2 | 24.5 | 23.2 | 21.8 |
| 12 | 24.8 | 19.9 | 19.1 | 20.2 | 20.9 | 19.3 | 18.8 |

Mean max-drawdown is **−65% to −81% in EVERY cell** (including the best).

## Conclusions

1. **Shorter beats the 12/12 default.** Best region = lookback ~8–11mo + hold
   ~6–9mo (~27–33% CAGR), clearly above conventional L12/H12 (18.8%). Best cell
   L=10/H=6 = 33.3%. Consistent with momentum decay: a 12-month hold is too slow
   for single-name momentum; faster signal + faster rotation captures more.
2. **L and H move RETURN, not RISK.** Drawdowns ~−70% across the whole grid —
   2.5–3× the index. No lookback/hold combo escapes single-stock concentration.
3. **Don't over-trust the optimum.** One 14-year path; even phase-averaged the
   best cell ranges 2%–44% CAGR by start month (L12/H12: −12%–54%). Read the
   region (short-ish L and H help), not the exact L=10/H=6 — partly in-sample
   noise. The durable fix for the −70% drawdowns is still diversification, not
   signal tuning.

Run: `python src/lookback_hold_grid.py`

## P6 correction — 12/12 is anchor-dependent, not weak

The phase-averaging above understates 12/12. Annual rotation trades only ONCE a
year, so it is uniquely sensitive to the anchor month, and 12-month-lookback is
special precisely at **Dec-31** (trailing-12mo = the calendar-year winner that
ran hot 2012-26). Fixing the Dec-31 anchor (H=12):

| lookback | CAGR | maxDD |
|---|---|---|
| 6 | 47.7% | −55% |
| 8 | 53.1% | −52% |
| 9 | 54.4% | −62% |
| 10 | **57.9%** | −54% |
| **12** | **53.7%** | **−44%** |

So at its natural anchor, **12/12 = 53.7% and has the LOWEST drawdown (−44%)** —
near-optimal; L=10 only edges it on return with worse risk. The P6 phase-average
penalised 12/12 for anchor-fragility, not for being a poor rule. Correct reading:
**shorter holds are more ROBUST to when you rebalance (higher phase-average), but
do not have a higher ceiling than 12/12-at-year-end.** Both still carry ~−50%+
single-stock drawdowns.
