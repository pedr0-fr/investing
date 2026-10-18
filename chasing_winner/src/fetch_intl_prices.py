"""Fetch weekly (or other interval) prices for the international large-cap
universe (data/universe_intl.csv) via Yahoo's chart API.

Reuses fetch_prices.fetch_one (explicit period1/period2, adjusted closes,
backoff). Resumable: partials flushed to data/_partials_intl_<interval>/.
Output: data/prices_intl_<interval>.parquet.
"""
import argparse
import glob
import os
import time

import pandas as pd

import fetch_prices as fp

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")


def already_done(pdir):
    done = set()
    for p in glob.glob(os.path.join(pdir, "part_*.parquet")):
        try:
            done.update(pd.read_parquet(p, columns=["ticker"])["ticker"].unique())
        except Exception:
            pass
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", default="1wk", choices=["1d", "1wk", "1mo"])
    ap.add_argument("--batch", type=int, default=150)
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--combine-only", action="store_true")
    args = ap.parse_args()

    pdir = os.path.join(DATA, f"_partials_intl_{args.interval}")
    os.makedirs(pdir, exist_ok=True)
    out = os.path.join(DATA, f"prices_intl_{args.interval}.parquet")

    def combine():
        parts = sorted(glob.glob(os.path.join(pdir, "part_*.parquet")))
        if not parts:
            print("no partials")
            return
        df = pd.concat((pd.read_parquet(p) for p in parts), ignore_index=True)
        df = df.drop_duplicates(["date", "ticker"]).sort_values(["ticker", "date"])
        df.to_parquet(out, index=False)
        df["date"] = pd.to_datetime(df["date"])
        print(f"\ncombined -> {out}\n  rows {len(df):,} | tickers {df['ticker'].nunique():,} "
              f"| span {df['date'].min().date()}..{df['date'].max().date()}")

    if args.combine_only:
        return combine()

    uni = pd.read_csv(os.path.join(DATA, "universe_intl.csv"))
    tickers = sorted(uni["ticker"].astype(str).str.strip().unique())
    done = already_done(pdir)
    todo = [t for t in tickers if t not in done]
    print(f"universe={len(tickers)} done={len(done)} todo={len(todo)} "
          f"interval={args.interval}", flush=True)

    part_i = len(glob.glob(os.path.join(pdir, "part_*.parquet")))
    buf, with_data, t0 = [], 0, time.time()
    for i, sym in enumerate(todo, 1):
        df = fp.fetch_one(sym, args.interval)
        if df is not None and len(df):
            buf.append(df)
            with_data += 1
        if i % args.batch == 0 or i == len(todo):
            if buf:
                outp = os.path.join(pdir, f"part_{part_i:04d}.parquet")
                pd.concat(buf, ignore_index=True).to_parquet(outp, index=False)
                part_i += 1
                buf = []
            rate = i / max(time.time() - t0, 1e-9)
            print(f"[{i}/{len(todo)}] with_data={with_data} rate={rate:.1f}/s "
                  f"eta={(len(todo)-i)/max(rate,1e-9)/60:.0f}m", flush=True)
        time.sleep(args.sleep)

    combine()


if __name__ == "__main__":
    main()
