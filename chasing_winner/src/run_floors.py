"""Part B — ≥$20B vs ≥$40B market-cap floor comparison on REAL historical caps.

Universe at month m = point-in-time S&P 500 members then, further filtered to
real market cap (SEC shares-outstanding as-of m x price at m) >= floor.
Hold 12 mo, no stop, trailing-12m signal. Baskets of 3 and 4 (plus 5,6).
Window defaults to 2010-2026 (SEC XBRL shares start ~2009).

CAVEAT: still missing prices for members that delisted (survivor bias), but
selection + the cap floor are now point-in-time and real. Printed on each run.
"""
import argparse
import os

import numpy as np
import pandas as pd

import engine
import momentum_basket as mb
import sp500_membership as spm

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")


def monthly_cap(panel):
    """DataFrame [month x ticker] of real market cap = shares_asof * price."""
    sec = pd.read_parquet(os.path.join(DATA, "sec_shares.parquet"))
    sh = sec.pivot(index="date", columns="ticker", values="shares")
    idx = sh.index.union(panel.index)
    sh = sh.reindex(idx).sort_index().ffill().reindex(panel.index)
    cols = panel.columns.intersection(sh.columns)
    return panel[cols] * sh[cols]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2010)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--hold", type=int, default=12)
    ap.add_argument("--signal-lookback", type=int, default=12)
    ap.add_argument("--min-price", type=float, default=0.0)  # S&P members are liquid; $-floor on adj prices drops split winners
    ap.add_argument("--floors", type=float, nargs="+", default=[20.0, 40.0])
    ap.add_argument("--sizes", type=int, nargs="+", default=[3, 4, 5, 6])
    ap.add_argument("--start-cash", type=float, default=100.0)
    a = ap.parse_args()

    panel = mb.load_panel()
    cap = monthly_cap(panel)                      # $ market cap per month/ticker
    sets = spm.member_sets(panel.index, panel.columns)

    start_i = max(int(np.searchsorted(panel.index, np.datetime64(f"{a.start}-01"))),
                  a.signal_lookback)
    end_i = min(int(np.searchsorted(panel.index, np.datetime64(f"{a.end}-12"))),
                len(panel.index) - 1)

    bench = mb.load_benchmark().reindex(panel.index[start_i:end_i + 1]).ffill().bfill()
    bench = bench / bench.iloc[0]

    print(f"\nPart B | point-in-time S&P members + REAL cap floor (SEC shares) | "
          f"hold={a.hold}mo no-stop signal={a.signal_lookback}mo | {a.start}-{a.end}")
    print("!! missing delisted-member prices -> residual survivor bias\n")

    # diagnostic: eligible names clearing each floor (year-end)
    for f in a.floors:
        floor = f * 1e9
        counts = {}
        for mi in range(start_i, end_i + 1, 12):
            el = sets[mi] & set(cap.columns[(cap.iloc[mi] >= floor).values])
            counts[panel.index[mi].year] = len(el)
        print(f"  ≥${f:.0f}B eligible-count by year: {counts}")
    print()

    print("| floor | basket n | final $ | CAGR % | maxDD % | rotations |")
    print("|---|---|---|---|---|---|")
    out_rows = []
    for f in a.floors:
        floor = f * 1e9
        cap_ok = {mi: set(cap.columns[(cap.iloc[mi] >= floor).values])
                  for mi in range(start_i, end_i + 1)}
        eligible_at = lambda mi, _c=cap_ok: sets[mi] & _c[mi]
        for n in a.sizes:
            eq, tr = engine.simulate(panel, eligible_at, n=n, hold=a.hold,
                                     signal_lookback=a.signal_lookback,
                                     min_price=a.min_price, start_i=start_i,
                                     end_i=end_i)
            print(f"| ≥${f:.0f}B | {n} | ${eq.iloc[-1]*a.start_cash:,.0f} | "
                  f"{engine.cagr(eq)*100:.1f} | {engine.max_drawdown(eq)*100:.0f} | "
                  f"{len(tr)-1} |")
            out_rows.append((f, n, eq))
    print(f"| **S&P 500** | - | **${bench.iloc[-1]*a.start_cash:,.0f}** | "
          f"**{engine.cagr(bench)*100:.1f}** | "
          f"**{engine.max_drawdown(bench)*100:.0f}** | - |")

    os.makedirs(RESULTS, exist_ok=True)
    for f, n, eq in out_rows:
        (eq * a.start_cash).to_csv(
            os.path.join(RESULTS, f"floors_{a.start}_{a.end}_f{int(f)}_n{n}.csv"))
    print("\nsaved results/floors_*.csv")


if __name__ == "__main__":
    main()
