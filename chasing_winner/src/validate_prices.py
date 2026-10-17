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


def main():
    import os
    import sys as _sys
    interval = _sys.argv[1] if len(_sys.argv) > 1 else "1wk"   # default = weekly
    df = pd.read_parquet(os.path.join(
        os.path.dirname(__file__), "..", "data", f"prices_{interval}.parquet"))
    print(f"[validating prices_{interval}.parquet]")
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year

    # expected bars in a full year; "downsampled" = far below that
    full = 52 if interval == "1wk" else 12
    down_thr = full // 4          # <=1/4 of expected -> coarser frequency
    gap_thr = int(full * 0.85)    # <85% of expected -> missing bars

    first = df.groupby("ticker")["year"].min()
    last = df.groupby("ticker")["year"].max()
    per_year = df.groupby(["ticker", "year"]).size().rename("n").reset_index()

    downsampled = set()
    gappy = set()
    for t, g in per_year.groupby("ticker"):
        interior = g[(g["year"] > first[t]) & (g["year"] < last[t])]
        if len(interior) == 0:
            continue
        if (interior["n"] <= down_thr).mean() > 0.5:
            downsampled.add(t)
        elif (interior["n"] < gap_thr).mean() > 0.2:
            gappy.add(t)

    n = df["ticker"].nunique()
    print(f"tickers: {n}  (expect ~{full} bars/full-year)")
    print(f"  DOWNSAMPLED (<= {down_thr}/yr): {len(downsampled)}"
          + (f"  e.g. {sorted(downsampled)[:10]}" if downsampled else ""))
    print(f"  gappy (< {gap_thr}/yr):      {len(gappy)}"
          + (f"  e.g. {sorted(gappy)[:10]}" if gappy else ""))
    clean = n - len(downsampled) - len(gappy)
    print(f"  clean:                   {clean}  ({100*clean/n:.0f}%)")

    bad = len(downsampled) + len(gappy)
    if bad > 0.02 * n:
        print(f"\nFAIL: {bad} tickers not clean ({interval}) (> 2% of universe).")
        return 1
    print(f"\nOK: panel is clean {interval}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
