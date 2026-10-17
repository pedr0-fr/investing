"""Part A — overlapping momentum basket on point-in-time S&P 500 membership.

Universe at each month = actual S&P 500 members then (survivorship-free
membership), restricted to names we have prices for. No explicit $ floor.
Hold 12 mo, no stop, trailing-12m signal. Compares baskets of 3 and 4 (and a
couple extras) vs the S&P 500, 1996-2026.

CAVEAT: ~42% of ever-members (the failures) have no free price series, so this
is still biased toward survivors. Printed on every run.
"""
import argparse
import os

import numpy as np
import pandas as pd

import engine
import momentum_basket as mb
import sp500_membership as spm

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1996)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--hold", type=int, default=12)
    ap.add_argument("--signal-lookback", type=int, default=12)
    ap.add_argument("--min-price", type=float, default=5.0)
    ap.add_argument("--sizes", type=int, nargs="+", default=[3, 4, 5, 6])
    ap.add_argument("--start-cash", type=float, default=100.0)
    a = ap.parse_args()

    panel = mb.load_panel()
    sets = spm.member_sets(panel.index, panel.columns)
    eligible_at = lambda mi: sets[mi]

    start_i = int(np.searchsorted(panel.index, np.datetime64(f"{a.start}-01")))
    start_i = max(start_i, a.signal_lookback)
    end_i = min(int(np.searchsorted(panel.index, np.datetime64(f"{a.end}-12"))),
                len(panel.index) - 1)

    print(f"\nPart A | point-in-time S&P 500 membership universe | "
          f"hold={a.hold}mo no-stop signal={a.signal_lookback}mo | "
          f"{a.start}-{a.end} | ${a.start_cash:.0f}")
    print("members-with-prices by year:",
          spm.coverage_report(sets, panel.index))
    print("!! ~42% of ever-members (failures) have no free prices -> survivor-biased\n")

    bench = mb.load_benchmark().reindex(panel.index[start_i:end_i + 1]).ffill().bfill()
    bench = bench / bench.iloc[0]

    print("| basket n | final $ | CAGR % | maxDD % | rotations |")
    print("|---|---|---|---|---|")
    rows = []
    for n in a.sizes:
        eq, tr = engine.simulate(panel, eligible_at, n=n, hold=a.hold,
                                 signal_lookback=a.signal_lookback,
                                 min_price=a.min_price, start_i=start_i,
                                 end_i=end_i)
        rows.append((n, eq, tr))
        print(f"| {n} | ${eq.iloc[-1]*a.start_cash:,.0f} | "
              f"{engine.cagr(eq)*100:.1f} | {engine.max_drawdown(eq)*100:.0f} | "
              f"{len(tr)-1} |")
    print(f"| **S&P 500** | **${bench.iloc[-1]*a.start_cash:,.0f}** | "
          f"**{engine.cagr(bench)*100:.1f}** | "
          f"**{engine.max_drawdown(bench)*100:.0f}** | - |")

    os.makedirs(RESULTS, exist_ok=True)
    for n, eq, tr in rows:
        (eq * a.start_cash).to_csv(
            os.path.join(RESULTS, f"membership_{a.start}_{a.end}_n{n}.csv"))
    print("\nsaved results/membership_*.csv")


if __name__ == "__main__":
    main()
