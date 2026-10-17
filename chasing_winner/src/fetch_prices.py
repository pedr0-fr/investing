"""Download and store historical prices for the whole universe.

yfinance's preliminary metadata endpoints get rate-limited hard in this
environment, so we hit Yahoo's public chart API directly (it returns
split/dividend-adjusted closes) with host fallback + exponential backoff.

Design goals:
  * RESUMABLE  - progress is flushed to data/_partials_<interval>/part_XXXX.parquet
                 every --batch tickers; a rerun skips tickers already stored,
                 so throttling or a crash never costs more than one partial.
  * GENTLE     - per-request sleep + exponential backoff on HTTP 429.
  * REUSABLE   - stored long-format [date, ticker, close] with ADJUSTED closes,
                 so winner-selection logic can change without re-downloading.

Default interval is monthly (enough to pick the annual winner and approximate
the 35% stop). Use --interval 1d for precise intra-year stop modelling on the
small set of names actually held.

Usage:
  python fetch_prices.py [--interval 1mo|1wk|1d] [--batch 200] [--sleep 0.4]
                         [--limit N] [--common-only] [--combine-only]
"""
import argparse
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
HOSTS = ("query1", "query2")


def load_tickers(limit, common_only):
    uni = os.path.join(DATA, "universe.csv")
    if not os.path.exists(uni):
        sys.exit("universe.csv missing - run build_universe.py first")
    df = pd.read_csv(uni)
    if common_only:
        df = df[df["is_common_guess"] == 1]
    syms = df["symbol"].astype(str).str.strip()
    syms = sorted(s for s in syms if s and s.isascii())
    return syms[:limit] if limit else syms


def already_done(partials_dir):
    done = set()
    for p in glob.glob(os.path.join(partials_dir, "part_*.parquet")):
        try:
            done.update(pd.read_parquet(p, columns=["ticker"])["ticker"].unique())
        except Exception:
            pass
    return done


def fetch_one(sym, interval, retries=4):
    """Return a DataFrame[date, ticker, close] for one symbol, or None."""
    delay = 1.5
    for attempt in range(1, retries + 1):
        host = HOSTS[(attempt - 1) % len(HOSTS)]
        url = (f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}"
               f"?interval={interval}&range=max&events=splits")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            res = (d.get("chart") or {}).get("result")
            if not res:
                return None  # genuinely empty (delisted / no data)
            res = res[0]
            ts = res.get("timestamp")
            if not ts:
                return None
            ind = res["indicators"]
            adj = (ind.get("adjclose") or [{}])[0].get("adjclose")
            close = adj if adj is not None else ind["quote"][0]["close"]
            dates = pd.to_datetime(ts, unit="s").normalize()
            out = pd.DataFrame({"date": dates, "ticker": sym, "close": close})
            return out.dropna(subset=["close"])
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(delay)
                delay *= 2
                continue
            if e.code in (404, 400):
                return None
            time.sleep(delay)
            delay *= 2
        except Exception:
            time.sleep(delay)
            delay *= 2
    return None


def combine(partials_dir, interval):
    parts = sorted(glob.glob(os.path.join(partials_dir, "part_*.parquet")))
    if not parts:
        print("no partials to combine")
        return
    df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
    df = df.drop_duplicates(["date", "ticker"]).sort_values(["ticker", "date"])
    out = os.path.join(DATA, f"prices_{interval}.parquet")
    df.to_parquet(out, index=False)
    print(f"\ncombined -> {out}")
    print(f"  rows:     {len(df):,}")
    print(f"  tickers:  {df['ticker'].nunique():,}")
    if len(df):
        df["date"] = pd.to_datetime(df["date"])
        print(f"  span:     {df['date'].min().date()} .. {df['date'].max().date()}")
    else:
        print("  span:     (no data)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", default="1mo", choices=["1d", "1wk", "1mo"])
    ap.add_argument("--batch", type=int, default=200)
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--common-only", action="store_true")
    ap.add_argument("--combine-only", action="store_true")
    args = ap.parse_args()

    partials_dir = os.path.join(DATA, f"_partials_{args.interval}")
    os.makedirs(partials_dir, exist_ok=True)

    if args.combine_only:
        combine(partials_dir, args.interval)
        return 0

    tickers = load_tickers(args.limit, args.common_only)
    done = already_done(partials_dir)
    todo = [t for t in tickers if t not in done]
    print(f"universe={len(tickers)}  done={len(done)}  todo={len(todo)}  "
          f"interval={args.interval}  batch={args.batch}", flush=True)

    existing = len(glob.glob(os.path.join(partials_dir, "part_*.parquet")))
    buf, with_data, part_i, t0 = [], 0, existing, time.time()

    def flush():
        nonlocal buf, part_i
        if not buf:
            return
        df = (pd.concat(buf, ignore_index=True) if any(len(b) for b in buf)
              else pd.DataFrame(columns=["date", "ticker", "close"]))
        out = os.path.join(partials_dir, f"part_{part_i:04d}.parquet")
        df.to_parquet(out, index=False)
        print(f"  -> {out}  rows={len(df):,}", flush=True)
        buf, part_i = [], part_i + 1

    for i, sym in enumerate(todo, 1):
        df = fetch_one(sym, args.interval)
        if df is not None and len(df):
            buf.append(df)
            with_data += 1
        if i % args.batch == 0:
            rate = i / max(time.time() - t0, 1e-9)
            eta = (len(todo) - i) / max(rate, 1e-9) / 60
            print(f"[{i}/{len(todo)}] with_data={with_data} "
                  f"rate={rate:.1f}/s eta={eta:.0f}m", flush=True)
            flush()
        time.sleep(args.sleep)
    flush()

    combine(partials_dir, args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
