"""Freshness guard for the price panels. Weekly is the default dataset.

Prints the last bar date of each panel and whether it is stale relative to a
reference date (pass --today YYYY-MM-DD; the harness knows the real date).
Convention: before running a new analysis, check this; if the default (weekly)
panel is stale, propose a refresh (`fetch_prices.py --interval 1wk`) first.

Stale threshold: weekly > 10 days behind reference; monthly > 45 days.
"""
import argparse
import os
import sys

import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
THRESH_DAYS = {"1wk": 10, "1mo": 45}


def last_bar(interval):
    path = os.path.join(DATA, f"prices_{interval}.parquet")
    if not os.path.exists(path):
        return None
    d = pd.read_parquet(path, columns=["date"])
    return pd.to_datetime(d["date"]).max()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None, help="reference date YYYY-MM-DD")
    a = ap.parse_args()
    today = pd.Timestamp(a.today) if a.today else pd.Timestamp.utcnow().normalize()

    stale_default = False
    print(f"reference date: {today.date()}")
    for interval in ("1wk", "1mo"):
        lb = last_bar(interval)
        if lb is None:
            print(f"  {interval}: MISSING")
            continue
        age = (today - lb).days
        thr = THRESH_DAYS[interval]
        status = "STALE" if age > thr else "ok"
        star = "  <-- DEFAULT" if interval == "1wk" else ""
        print(f"  {interval}: last bar {lb.date()}  ({age}d old, thr {thr}d)  {status}{star}")
        if interval == "1wk" and status == "STALE":
            stale_default = True

    if stale_default:
        print("\nDEFAULT (weekly) IS STALE -> propose refresh before further tasks:")
        print("  python src/fetch_prices.py --interval 1wk --batch 200 --sleep 0.3")
        return 1
    print("\nweekly panel is current.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
