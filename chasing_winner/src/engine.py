"""Generalized overlapping-basket simulation with TIME-VARYING eligibility.

The difference from momentum_basket.simulate (static eligible set) is that
`eligible_at(mi)` returns the set of eligible tickers at month index `mi`.
This lets us plug in point-in-time S&P 500 membership and/or a historical
market-cap floor without duplicating the sim loop.
"""
import numpy as np
import pandas as pd


def best_momentum(panel, elig, mi, lookback, held, min_price):
    """Top trailing-`lookback`-month return among `elig`, priced, not held."""
    if mi - lookback < 0:
        return None
    now, then = panel.iloc[mi], panel.iloc[mi - lookback]
    best_t, best_r = None, -np.inf
    for t in elig:
        if t in held or t not in panel.columns:
            continue
        p_now, p_then = now.get(t), then.get(t)
        if pd.isna(p_now) or pd.isna(p_then) or p_then <= 0 or p_now < min_price:
            continue
        r = p_now / p_then - 1
        if r > best_r:
            best_t, best_r = t, r
    return best_t


def simulate(panel, eligible_at, *, n, hold, signal_lookback, min_price,
             start_i, end_i):
    """Returns (equity Series, trades list). Equal-capital staggered slots."""
    step = max(1, round(hold / n))
    slot_cap = 1.0 / n
    slots, held = [], set()

    for k in range(n):
        elig = eligible_at(start_i)
        t = best_momentum(panel, elig, start_i, signal_lookback, held, min_price)
        if t is None:
            raise SystemExit("not enough eligible names at start")
        held.add(t)
        slots.append({"ticker": t, "value": slot_cap,
                      "next_rot": start_i + (k + 1) * step})

    trades = [(panel.index[start_i], "INIT", [s["ticker"] for s in slots])]
    eq_dates, eq_vals = [], []

    for mi in range(start_i, end_i + 1):
        if mi > start_i:
            prev, cur = panel.iloc[mi - 1], panel.iloc[mi]
            for s in slots:
                p0, p1 = prev.get(s["ticker"]), cur.get(s["ticker"])
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    s["value"] *= p1 / p0
        for s in slots:
            if mi >= s["next_rot"] and mi < end_i:
                held.discard(s["ticker"])
                elig = eligible_at(mi)
                new_t = best_momentum(panel, elig, mi, signal_lookback, held,
                                      min_price)
                if new_t is not None:
                    trades.append((panel.index[mi], f"{s['ticker']}->{new_t}", None))
                    s["ticker"] = new_t
                    held.add(new_t)
                else:
                    held.add(s["ticker"])
                s["next_rot"] = mi + hold
        eq_dates.append(panel.index[mi])
        eq_vals.append(sum(s["value"] for s in slots))

    return pd.Series(eq_vals, index=pd.DatetimeIndex(eq_dates)), trades


def max_drawdown(equity):
    return float((equity / equity.cummax() - 1).min())


def cagr(equity):
    """Frequency-agnostic CAGR from the actual date span (works for weekly or
    monthly indices). Falls back to assuming monthly if the index isn't dated."""
    idx = equity.index
    try:
        yrs = (idx[-1] - idx[0]).days / 365.25
    except (AttributeError, TypeError):
        yrs = len(equity) / 12.0
    if yrs <= 0:
        return float("nan")
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / yrs) - 1
