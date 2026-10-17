"""Reconcile our backtest with the thread's '2012winners' chart.

The chart (Exhibit 3) compounds, for each year, the CALENDAR-YEAR price return
of the S&P 500's actual best prior-year performer, implicitly entering at the
prior Dec-31 close. Its printed next-year figures compound to ~1,212x.

This script reproduces the chart's METHOD on our data (calendar-year selection
by Dec->Dec return, Dec-31 entry) so the remaining gap is attributable to
data/survivorship rather than method/timing. Contrast with run_membership.py
--sizes 1 (our mechanical January-rebalance version), which lands ~25x.
"""
import numpy as np
import pandas as pd

import momentum_basket as mb
import sp500_membership as spm

# chart's picks (held in year Y = winner of Y-1) and printed next-year gains %
CHART = {2013:("PHM",12),2014:("NFLX",-7),2015:("LUV",2),2016:("NFLX",8),
         2017:("NVDA",81),2018:("NRG",39),2019:("AMD",148),2020:("AMD",100),
         2021:("TSLA",50),2022:("DVN",40),2023:("OXY",-5),2024:("NVDA",171),
         2025:("PLTR",135),2026:("SNDK",566)}


def main():
    panel = mb.load_panel(interval="1mo")
    sets = spm.member_sets(panel.index, panel.columns)

    def dec(y):
        return min(int(np.searchsorted(panel.index, np.datetime64(f"{y}-12"))),
                   len(panel.index) - 1)

    def ret(t, i0, i1):
        a, b = panel.at[panel.index[i0], t], panel.at[panel.index[i1], t]
        return (b / a - 1) if (a == a and b == b and a > 0) else np.nan

    chart_cmp = 1.0
    for y in CHART:
        chart_cmp *= 1 + CHART[y][1] / 100

    print("Reconciliation: thread chart vs our data (calendar-year, Dec-31 entry)\n")
    print(f"{'held':5} {'our winner':10} {'our%':>6}  {'chart pick':10} {'chart%':>6}")
    eq, match = 1.0, 0
    for Y in range(2013, 2027):
        iD0, iD1, iDh = dec(Y - 2), dec(Y - 1), dec(Y)
        if iD1 - iD0 < 6:
            continue
        best, br = None, -9.0
        for t in sets[iD1]:
            if t not in panel.columns:
                continue
            p1 = panel.at[panel.index[iD1], t]
            if p1 != p1:                 # NO $-floor on split-ADJUSTED prices:
                continue                 # it wrongly drops split-heavy winners
            r = ret(t, iD0, iD1)         # (NVDA's adj 2016 price is ~$0.27)
            if r == r and r > br:
                br, best = r, t
        held = ret(best, iD1, iDh)
        held = 0.0 if held != held else held
        eq *= 1 + held
        cp, cr = CHART.get(Y, ("?", float("nan")))
        match += best == cp
        print(f"{Y:5} {str(best):10} {held*100:6.0f}  {cp:10} {cr:6.0f}"
              f"{'  <-- match' if best == cp else ''}")

    print(f"\nour calendar-method : ${100*eq:,.0f}  ({eq:,.0f}x)   picks matching: {match}/14")
    print(f"chart's own figures  : ${100*chart_cmp:,.0f}  ({chart_cmp:,.0f}x)")
    print("\nGap decomposition (on clean monthly data):")
    print("  entry timing: a Dec-31 entry ~doubles a Jan entry on parabolic names")
    print("  remaining pick mismatches are IPO/spinoff-measurement cases (e.g. SNDK")
    print("  2026, the chart measures from its Feb-2025 debut).")
    print("  the chart also assumes zero cost/slippage/tax and a single-stock bet.")


if __name__ == "__main__":
    main()
