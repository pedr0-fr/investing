"""P1 — overlapping (staggered) momentum basket.

Refinement of 'Chasing the Winner' per the spec:
  * Universe: mid-cap BAND [--mktcap-min, --mktcap-max] $B, common stocks.
  * N slots (--n), each equal-capital, no stop-loss.
  * Each slot holds one name for --hold months, then rotates into the current
    best trailing-momentum name not already held.
  * Rotations are STAGGERED: one slot comes due every `step = hold/n` months,
    so we rotate one position at a time instead of the whole book at once.
  * Each slot compounds its own capital independently (realistic "sell this
    one, reinvest its proceeds into the replacement").

Signal: trailing --signal-lookback month total return (default 12), i.e.
classic cross-sectional momentum.

CAVEAT (unchanged from P0): the market-cap band uses *current* market cap and
the universe is current listings -> survivorship + look-ahead bias. Directional
only until we have point-in-time constituents. Printed on every run.

Usage:
  python momentum_basket.py --n 6 --hold 12 --signal-lookback 12 \
      --mktcap-min 5 --mktcap-max 50 --start 2012 --end 2026
"""
import argparse
import json
import os
import sys
import urllib.request

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "..", "results")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def load_panel(interval="1wk"):
    """Load a wide month x ticker (or week x ticker) price panel.

    Default is WEEKLY (the canonical dataset). Month-anchored analyses pass
    interval="1mo" to preserve month-end semantics / documented results.
    """
    df = pd.read_parquet(os.path.join(DATA, f"prices_{interval}.parquet"))
    df["date"] = pd.to_datetime(df["date"])
    if interval == "1mo":
        df["date"] = df["date"].values.astype("datetime64[M]")  # stamp month-start
    panel = (df.drop_duplicates(["date", "ticker"])
               .pivot(index="date", columns="ticker", values="close")
               .sort_index())
    return panel


def eligible_set(mktcap_min, mktcap_max):
    uni = pd.read_csv(os.path.join(DATA, "universe.csv"))
    uni = uni[uni["is_common_guess"] == 1]
    mc = pd.to_numeric(uni["marketCap"], errors="coerce") / 1e9
    band = uni[(mc >= mktcap_min) & (mc <= mktcap_max)]
    return set(band["symbol"])


def load_benchmark():
    cache = os.path.join(DATA, "benchmark_gspc_1mo.parquet")
    if os.path.exists(cache):
        b = pd.read_parquet(cache)
    else:
        # explicit window (not range=max, which Yahoo downsamples to quarterly)
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
               "?interval=1mo&period1=315532800&period2=1790000000")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        res = d["chart"]["result"][0]
        dates = pd.to_datetime(res["timestamp"], unit="s")
        adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
        close = adj if adj is not None else res["indicators"]["quote"][0]["close"]
        b = pd.DataFrame({"date": dates, "close": close}).dropna()
        b.to_parquet(cache, index=False)
    b["date"] = pd.to_datetime(b["date"]).values.astype("datetime64[M]")
    return b.drop_duplicates("date").set_index("date")["close"].sort_index()


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def pick(panel, elig, mi, lookback, held, min_price):
    """Best trailing-`lookback`-month return at month index mi, among eligible,
    priced, not currently held."""
    if mi - lookback < 0:
        return None
    now = panel.iloc[mi]
    then = panel.iloc[mi - lookback]
    best_t, best_r = None, -np.inf
    for t in elig:
        if t in held or t not in panel.columns:
            continue
        p_now, p_then = now.get(t), then.get(t)
        if pd.isna(p_now) or pd.isna(p_then) or p_then <= 0:
            continue
        if p_now < min_price:
            continue
        r = p_now / p_then - 1
        if r > best_r:
            best_t, best_r = t, r
    return best_t


def simulate(args, panel=None, elig=None):
    """Run the overlapping-basket sim. Returns (equity Series, trades list)."""
    if panel is None:
        panel = load_panel(interval="1mo")
    if elig is None:
        elig = eligible_set(args.mktcap_min, args.mktcap_max)
    months = panel.index
    start_i = int(np.searchsorted(months, np.datetime64(f"{args.start}-01")))
    end_i = int(np.searchsorted(months, np.datetime64(f"{args.end}-12"))) - 1
    end_i = min(end_i, len(months) - 1)
    start_i = max(start_i, args.signal_lookback)

    step = max(1, round(args.hold / args.n))
    slot_cap = 1.0 / args.n
    slots = []  # each: {ticker, value, next_rot}
    held = set()

    # initialise N slots at start_i, staggered first-rotation dates
    for k in range(args.n):
        t = pick(panel, elig, start_i, args.signal_lookback, held, args.min_price)
        if t is None:
            sys.exit("not enough eligible names at start; widen the band")
        held.add(t)
        slots.append({"ticker": t, "value": slot_cap,
                      "next_rot": start_i + (k + 1) * step})

    trades = [(months[start_i], "INIT", [s["ticker"] for s in slots])]
    eq_dates, eq_vals = [], []

    for mi in range(start_i, end_i + 1):
        # grow each slot by this month's return (skip the entry month itself)
        if mi > start_i:
            prev, cur = panel.iloc[mi - 1], panel.iloc[mi]
            for s in slots:
                t = s["ticker"]
                p0, p1 = prev.get(t), cur.get(t)
                if pd.notna(p0) and pd.notna(p1) and p0 > 0:
                    s["value"] *= p1 / p0
                # if price missing (delisted mid-hold) -> hold flat, rotate when due
        # rotations due this month (one slot per `step` months by construction)
        for s in slots:
            if mi >= s["next_rot"] and mi < end_i:
                held.discard(s["ticker"])
                new_t = pick(panel, elig, mi, args.signal_lookback, held,
                             args.min_price)
                if new_t is not None:
                    trades.append((months[mi], f"{s['ticker']}->{new_t}", None))
                    s["ticker"] = new_t
                    held.add(new_t)
                else:
                    held.add(s["ticker"])  # keep if nothing eligible
                s["next_rot"] = mi + args.hold
        eq_dates.append(months[mi])
        eq_vals.append(sum(s["value"] for s in slots))

    equity = pd.Series(eq_vals, index=pd.DatetimeIndex(eq_dates))
    return equity, trades


def cagr(e: pd.Series) -> float:
    return (e.iloc[-1] / e.iloc[0]) ** (12.0 / len(e)) - 1


def run(args):
    panel = load_panel(interval="1mo")
    elig = eligible_set(args.mktcap_min, args.mktcap_max)
    step = max(1, round(args.hold / args.n))
    equity, trades = simulate(args, panel, elig)
    bench = load_benchmark().reindex(equity.index).ffill().bfill()
    bench = bench / bench.iloc[0]

    cash = args.start_cash
    print("=" * 72)
    print("OVERLAPPING MOMENTUM BASKET (P1)")
    print(f"start=${cash:.0f}  {args.start}..{args.end}  n={args.n}  "
          f"hold={args.hold}mo  step={step}mo  signal={args.signal_lookback}mo  "
          f"cap=[{args.mktcap_min},{args.mktcap_max}]B  no-stop")
    print(f"eligible universe size: {len(elig)} names")
    print("!! current listings + current mktcap -> survivorship/look-ahead bias")
    print("=" * 72)
    print(f"FINAL  basket : ${equity.iloc[-1]*cash:,.0f}   "
          f"CAGR {cagr(equity)*100:.1f}%   maxDD {max_drawdown(equity)*100:.0f}%   "
          f"rotations {len(trades)-1}")
    print(f"FINAL  S&P 500: ${bench.iloc[-1]*cash:,.0f}   "
          f"CAGR {cagr(bench)*100:.1f}%   maxDD {max_drawdown(bench)*100:.0f}%")

    os.makedirs(RESULTS, exist_ok=True)
    tag = f"basket_{args.start}_{args.end}_n{args.n}_h{args.hold}_sig{args.signal_lookback}"
    out = pd.DataFrame({"equity": equity * cash, "bench": bench * cash})
    out.to_csv(os.path.join(RESULTS, f"{tag}.csv"))
    with open(os.path.join(RESULTS, f"{tag}_trades.txt"), "w") as f:
        for d, mv, extra in trades:
            f.write(f"{pd.Timestamp(d).date()}  {mv}  {extra or ''}\n")
    print(f"\nsaved results/{tag}.csv  (+ _trades.txt)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--hold", type=int, default=12, help="holding months 6-18")
    ap.add_argument("--signal-lookback", type=int, default=12)
    ap.add_argument("--mktcap-min", type=float, default=5.0)
    ap.add_argument("--mktcap-max", type=float, default=50.0)
    ap.add_argument("--min-price", type=float, default=5.0)
    ap.add_argument("--start", type=int, default=2012)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--start-cash", type=float, default=100.0)
    run(ap.parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(main())
