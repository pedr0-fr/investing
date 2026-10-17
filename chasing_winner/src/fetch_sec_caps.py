"""Fetch historical shares-outstanding from SEC EDGAR -> data/sec_shares.parquet.

For each S&P-500-ever-member we have prices for, pull the reported common
shares outstanding time series (XBRL, ~2009+). Combined with monthly price at
backtest time this yields a real point-in-time market cap, so we can apply
genuine ≥$20B / ≥$40B floors (2010+ only; no XBRL before ~2009).

SEC asks for a descriptive User-Agent and <=10 req/s; we sleep 0.12s.
"""
import json
import os
import time
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "chasing-winner research pedro.fr.22@gmail.com"}
CONCEPTS = [  # try in order; first that returns data wins
    ("dei", "EntityCommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesOutstanding"),
    ("us-gaap", "CommonStockSharesIssued"),
]


def get_json(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                    timeout=30) as r:
            return json.loads(r.read())
    except Exception:
        return None


def target_tickers():
    panel = pd.read_parquet(os.path.join(DATA, "prices_1mo.parquet"))
    have = set(panel["ticker"].unique())
    m = pd.read_csv(os.path.join(DATA, "sp500_ticker_start_end.csv"))
    ever = set(m["ticker"]) | set(m["ticker"].str.replace(".", "-", regex=False))
    return sorted(ever & have)


def cik_map():
    d = get_json("https://www.sec.gov/files/company_tickers.json")
    out = {}
    for v in d.values():
        out[v["ticker"].upper()] = int(v["cik_str"])
    return out


def shares_series(cik):
    for taxo, tag in CONCEPTS:
        url = (f"https://data.sec.gov/api/xbrl/companyconcept/"
               f"CIK{cik:010d}/{taxo}/{tag}.json")
        d = get_json(url)
        if not d:
            continue
        units = d.get("units", {})
        vals = units.get("shares") or next(iter(units.values()), [])
        rows = [(x["end"], x["val"]) for x in vals if x.get("val")]
        if rows:
            return rows
    return []


def main():
    tickers = target_tickers()
    cmap = cik_map()
    print(f"targets={len(tickers)}  cik_map={len(cmap)}", flush=True)
    recs, miss = [], []
    for i, t in enumerate(tickers, 1):
        cik = cmap.get(t.upper()) or cmap.get(t.replace("-", ".").upper())
        if cik is None:
            miss.append(t)
            continue
        for end, val in shares_series(cik):
            recs.append({"ticker": t, "date": end, "shares": val})
        if i % 100 == 0:
            print(f"[{i}/{len(tickers)}] records={len(recs)}", flush=True)
        time.sleep(0.12)
    df = pd.DataFrame(recs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    out = os.path.join(DATA, "sec_shares.parquet")
    df.to_parquet(out, index=False)
    print(f"\nwrote {out}  rows={len(df):,}  tickers={df['ticker'].nunique()}")
    print(f"span {df['date'].min().date()}..{df['date'].max().date()}  "
          f"no-CIK: {len(miss)}")


if __name__ == "__main__":
    main()
