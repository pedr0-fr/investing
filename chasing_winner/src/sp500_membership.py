"""Point-in-time S&P 500 membership -> per-month eligible ticker sets.

Uses data/sp500_ticker_start_end.csv (ticker, start_date, end_date). A ticker
is a member in month m if start_date <= m <= end_date (end_date blank = still
in). Only tickers that also exist in the price panel are kept (others have no
prices we can trade).
"""
import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def member_sets(panel_index, panel_cols):
    """Return list parallel to panel_index: set of eligible tickers per month."""
    m = pd.read_csv(os.path.join(DATA, "sp500_ticker_start_end.csv"))
    m["start_date"] = pd.to_datetime(m["start_date"])
    m["end_date"] = pd.to_datetime(m["end_date"])  # NaT if ongoing
    have = set(panel_cols)
    # normalize class-share dots to Yahoo-style dashes for matching
    m["t1"] = m["ticker"].str.replace(".", "-", regex=False)
    months = pd.DatetimeIndex(panel_index)
    sets = []
    for mo in months:
        mo_end = mo + pd.offsets.MonthEnd(0)  # panel months are stamped at mo-start
        active = m[(m["start_date"] <= mo_end) &
                   (m["end_date"].isna() | (m["end_date"] >= mo))]
        cands = set(active["ticker"]) | set(active["t1"])
        sets.append(cands & have)
    return sets


def coverage_report(sets, months):
    s = pd.Series([len(x) for x in sets], index=pd.DatetimeIndex(months))
    yr = s.groupby(s.index.year).last()
    return {int(y): int(v) for y, v in yr.items() if y % 5 == 0}
