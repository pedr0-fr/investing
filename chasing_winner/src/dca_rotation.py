"""DCA rotation test for the single-winner S&P strategy.

Question: the all-at-once rebalance is very sensitive to the exact date (Dec-31
vs Jan-31 ~doubles parabolic years). Does spreading the hand-off over 3 months
(DCA out of the old winner, into the new) reduce that sensitivity? And does the
month of the year you rotate matter?

For each rotation-anchor month M (Jan..Dec):
  * Selection: at anchor, winner = highest trailing-12m return among S&P members
    as of the prior month-end (no look-ahead), single name, repeats allowed.
  * ALL-AT-ONCE: move 100% into the new winner at month M.
  * DCA-3MO: target weight in the new winner ramps 1/3 -> 2/3 -> 1 over M, M+1,
    M+2 (rebalanced monthly); fully in until next year's month M.
  * No stop, no cost. Point-in-time S&P membership, clean monthly data.

CAGR is the fair comparator across anchors (start months differ by up to 11mo).

TIMING CONVENTION: monthly bars are dated the 1st but priced at the MONTH-END
close (verified: the 2012-01 bar = Jan-31 close). So an anchor labeled month M
means you TRADE AT THE CLOSE OF MONTH M-1 (= the start of month M) on that
month-end signal, then earn month M onward. I.e. "January" = trade Dec-31
(the chart's method); "February" = trade Jan-31; "April" = trade Mar-31.
"""
import numpy as np
import pandas as pd

import momentum_basket as mb
import sp500_membership as spm

START_YEAR, END_YEAR = 2012, 2026


def main():
    panel = mb.load_panel(interval="1mo")
    idx = panel.index
    cols = {t: i for i, t in enumerate(panel.columns)}
    P = panel.to_numpy()                      # months x tickers (NaN where absent)
    sets = spm.member_sets(idx, panel.columns)
    member_cidx = [np.array([cols[t] for t in s], dtype=int) for s in sets]

    def winner(as_of):
        """argmax trailing-12m return at index as_of among members then."""
        if as_of - 12 < 0:
            return -1
        ci = member_cidx[as_of]
        if len(ci) == 0:
            return -1
        p1, p0 = P[as_of, ci], P[as_of - 12, ci]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = p1 / p0 - 1
        r = np.where(np.isfinite(r) & (p0 > 0) & np.isfinite(p1), r, -np.inf)
        return int(ci[np.argmax(r)]) if np.isfinite(r.max()) else -1

    def mret(cidx, mi):
        if cidx < 0:
            return 0.0
        a, b = P[mi - 1, cidx], P[mi, cidx]
        return (b / a - 1) if (np.isfinite(a) and np.isfinite(b) and a > 0) else 0.0

    def simulate(anchor_month, dca):
        # anchor indices: months where month==anchor and year in window
        anchors = [mi for mi in range(13, len(idx))
                   if idx[mi].month == anchor_month
                   and START_YEAR <= idx[mi].year <= END_YEAR]
        if not anchors:
            return None
        s0 = anchors[0]
        # weight schedule: ramp of NEW-winner target weight per month index
        w_new_target = {}          # mi -> target weight of 'new' during transition
        pick_at = {}               # transition-start mi -> new cidx
        for aM in anchors:
            new_c = winner(aM - 1)
            pick_at[aM] = new_c
            if dca:
                for k, w in enumerate((1/3, 2/3, 1.0)):
                    if aM + k < len(idx):
                        w_new_target[aM + k] = (new_c, w)
            else:
                w_new_target[aM] = (new_c, 1.0)

        value = 1.0
        old_c = pick_at[s0]        # start fully in first winner
        new_c = old_c
        w_new = 1.0
        eq = []
        for mi in range(s0, len(idx)):
            # update targets if this month is part of a transition
            if mi in w_new_target:
                tc, tw = w_new_target[mi]
                if tw == 1/3 or not dca:       # first step: define old/new
                    if tc != new_c:            # genuine switch
                        old_c = new_c
                        new_c = tc
                        w_new = 0.0
                    else:
                        new_c = tc
                # advance weight toward target
                w_new = tw if (tc == new_c) else w_new
                if tc == new_c:
                    w_new = tw
            # apply this month's return with current blend
            w_old = 1 - w_new
            r = w_old * mret(old_c, mi) + w_new * mret(new_c, mi)
            value *= (1 + r)
            eq.append(value)
            # once fully transitioned, collapse old into new
            if w_new >= 0.999:
                old_c = new_c
                w_new = 1.0
        e = pd.Series(eq, index=idx[s0:len(idx)])
        yrs = len(e) / 12.0
        cagr = (e.iloc[-1]) ** (1 / yrs) - 1
        dd = float((e / e.cummax() - 1).min())
        return e.iloc[-1] * 100, cagr * 100, dd * 100, idx[s0].strftime("%Y-%m")

    bench = mb.load_benchmark()

    print(f"Single-winner S&P, {START_YEAR}-{END_YEAR}, clean data. "
          f"CAGR is the fair comparator.\n")
    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    for dca in (False, True):
        tag = "DCA over 3 months" if dca else "ALL-AT-ONCE (1 month)"
        print(f"=== {tag} ===")
        print("| anchor | start | final $ | CAGR % | maxDD % |")
        print("|---|---|---|---|---|")
        cagrs = []
        for m in range(1, 13):
            res = simulate(m, dca)
            if not res:
                continue
            fin, cg, dd, st = res
            cagrs.append(cg)
            print(f"| {months[m-1]} | {st} | ${fin:,.0f} | {cg:.1f} | {dd:.0f} |")
        cagrs = np.array(cagrs)
        print(f"  -> CAGR mean {cagrs.mean():.1f}%  range {cagrs.min():.1f}..{cagrs.max():.1f}  "
              f"spread {cagrs.max()-cagrs.min():.1f}pp  std {cagrs.std():.1f}\n")

    # benchmark over the full window for reference
    b = bench.reindex(idx[(idx.year>=START_YEAR)]).ffill().bfill(); b=b/b.iloc[0]
    yrs=len(b)/12.0
    print(f"S&P 500 over window: CAGR {((b.iloc[-1])**(1/yrs)-1)*100:.1f}%  "
          f"maxDD {float((b/b.cummax()-1).min())*100:.0f}%")


if __name__ == "__main__":
    main()
