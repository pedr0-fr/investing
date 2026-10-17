"""Data-quality gate for the monthly price panel. Run BEFORE any backtest.

Checks each ticker for monthly completeness and flags:
  * QUARTERLY downsampling (<=5 points in a year that should be full) — the
    range=max bug that corrupted AAPL/DVN/etc.
  * internal gaps (missing months between first and last observation)

Exits non-zero if a material fraction of the universe is not clean monthly, so
it can be used as a guard in a pipeline.
"""
import sys

import pandas as pd

from momentum_basket import load_panel  # wide month x ticker not needed; use long


def main():
    df = pd.read_parquet("../data/prices_1mo.parquet") if False else \
        pd.read_parquet(__import__("os").path.join(
            __import__("os").path.dirname(__file__), "..", "data",
            "prices_1mo.parquet"))
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    # a "full" year for a ticker = one strictly between its first and last year
    first = df.groupby("ticker")["year"].min()
    last = df.groupby("ticker")["year"].max()
    per_year = df.groupby(["ticker", "year"]).size().rename("n").reset_index()

    quarterly = set()
    gappy = set()
    for t, g in per_year.groupby("ticker"):
        fy, ly = first[t], last[t]
        interior = g[(g["year"] > fy) & (g["year"] < ly)]
        if len(interior) == 0:
            continue
        if (interior["n"] <= 5).mean() > 0.5:      # majority of full years quarterly
            quarterly.add(t)
        elif (interior["n"] < 11).mean() > 0.2:    # >20% of full years missing months
            gappy.add(t)

    n = df["ticker"].nunique()
    print(f"tickers: {n}")
    print(f"  QUARTERLY (downsampled): {len(quarterly)}"
          + (f"  e.g. {sorted(quarterly)[:10]}" if quarterly else ""))
    print(f"  gappy (missing months):  {len(gappy)}"
          + (f"  e.g. {sorted(gappy)[:10]}" if gappy else ""))
    clean = n - len(quarterly) - len(gappy)
    print(f"  clean monthly:           {clean}  ({100*clean/n:.0f}%)")

    bad = len(quarterly) + len(gappy)
    if bad > 0.02 * n:
        print(f"\nFAIL: {bad} tickers not clean monthly (> 2% of universe).")
        return 1
    print("\nOK: panel is clean monthly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
