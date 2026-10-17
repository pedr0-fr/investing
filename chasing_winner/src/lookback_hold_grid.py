"""Lookback x holding-period grid for the single-winner S&P strategy.

Generalises the 12-month/12-month default: pick the winner on a trailing
L-month return and rotate every H months, for L,H in 6..12.

Because a single-stock result swings wildly with the start month (see P5), each
(L,H) cell is PHASE-AVERAGED: we run the strategy starting at every possible
month offset (0..H-1) and average across phases, so the number reflects the
rule rather than one lucky calendar alignment. We report mean CAGR (phase avg),
the phase spread, and mean max-drawdown.

Single name, no stop, point-in-time S&P membership, clean monthly data,
2012-2026. Timing convention as in dca_rotation.py (trade at prior month-end).
"""
import numpy as np
import pandas as pd

import momentum_basket as mb
import sp500_membership as spm

START_YEAR, END_YEAR = 2012, 2026
LOOKBACKS = range(6, 13)
HOLDS = range(6, 13)


def main():
    panel = mb.load_panel(interval="1mo")
    idx = panel.index
    cols = {t: i for i, t in enumerate(panel.columns)}
    P = panel.to_numpy()
    sets = spm.member_sets(idx, panel.columns)
    member_cidx = [np.array([cols[t] for t in s], dtype=int) for s in sets]

    base = next(mi for mi in range(len(idx))
                if idx[mi].year == START_YEAR and idx[mi].month == 1)
    end_i = max(mi for mi in range(len(idx)) if idx[mi].year <= END_YEAR)

    def winner(as_of, L):
        if as_of - L < 0:
            return -1
        ci = member_cidx[as_of]
        if len(ci) == 0:
            return -1
        p1, p0 = P[as_of, ci], P[as_of - L, ci]
        with np.errstate(invalid="ignore", divide="ignore"):
            r = p1 / p0 - 1
        r = np.where(np.isfinite(r) & (p0 > 0) & np.isfinite(p1), r, -np.inf)
        return int(ci[np.argmax(r)]) if np.isfinite(r.max()) else -1

    def mret(c, mi):
        if c < 0:
            return 0.0
        a, b = P[mi - 1, c], P[mi, c]
        return (b / a - 1) if (np.isfinite(a) and np.isfinite(b) and a > 0) else 0.0

    def run(L, H, phase):
        s0 = base + phase
        if s0 - 1 - L < 0:
            return None
        held = winner(s0 - 1, L)
        next_rot = s0 + H
        value, eq = 1.0, []
        for mi in range(s0, end_i + 1):
            if mi >= next_rot:
                w = winner(mi - 1, L)
                if w >= 0:
                    held = w
                next_rot = mi + H
            value *= 1 + mret(held, mi)
            eq.append(value)
        e = pd.Series(eq)
        yrs = len(e) / 12.0
        cagr = e.iloc[-1] ** (1 / yrs) - 1
        dd = float((e / e.cummax() - 1).min())
        return cagr * 100, dd * 100

    cagr_grid = {}
    dd_grid = {}
    for L in LOOKBACKS:
        for H in HOLDS:
            cs, ds = [], []
            for phase in range(H):
                res = run(L, H, phase)
                if res:
                    cs.append(res[0])
                    ds.append(res[1])
            cagr_grid[(L, H)] = (np.mean(cs), np.min(cs), np.max(cs))
            dd_grid[(L, H)] = np.mean(ds)

    bench = mb.load_benchmark().reindex(idx[(idx.year >= START_YEAR)]).ffill().bfill()
    bench = bench / bench.iloc[0]
    byr = len(bench) / 12.0
    bcagr = (bench.iloc[-1] ** (1 / byr) - 1) * 100
    bdd = float((bench / bench.cummax() - 1).min()) * 100

    print(f"Single-winner S&P, {START_YEAR}-{END_YEAR}, clean data, PHASE-AVERAGED.\n")
    print("MEAN CAGR % (phase-averaged over all start months)")
    print("rows=lookback L (mo), cols=hold H (mo)")
    print("       " + "".join(f"H={H:>5}" for H in HOLDS))
    for L in LOOKBACKS:
        print(f"  L={L:2} " + "".join(f"{cagr_grid[(L,H)][0]:6.1f}" for H in HOLDS))
    print(f"\n  (S&P 500 over window: CAGR {bcagr:.1f}%, maxDD {bdd:.0f}%)")

    print("\nMEAN max-drawdown % (phase-averaged)")
    print("       " + "".join(f"H={H:>5}" for H in HOLDS))
    for L in LOOKBACKS:
        print(f"  L={L:2} " + "".join(f"{dd_grid[(L,H)]:6.0f}" for H in HOLDS))

    best = max(cagr_grid, key=lambda k: cagr_grid[k][0])
    worst = min(cagr_grid, key=lambda k: cagr_grid[k][0])
    print(f"\nbest  mean-CAGR cell: L={best[0]} H={best[1]} -> "
          f"{cagr_grid[best][0]:.1f}% (phase range {cagr_grid[best][1]:.0f}..{cagr_grid[best][2]:.0f})")
    print(f"worst mean-CAGR cell: L={worst[0]} H={worst[1]} -> "
          f"{cagr_grid[worst][0]:.1f}%")
    b1212 = cagr_grid.get((12, 12))
    if b1212:
        print(f"baseline L=12 H=12: {b1212[0]:.1f}% (phase range {b1212[1]:.0f}..{b1212[2]:.0f})")


if __name__ == "__main__":
    main()
