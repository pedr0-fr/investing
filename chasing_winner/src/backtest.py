"""P0 backtester for 'Chasing the Winner'.

Honest-reproduction attempt of the gurgavin claim using monthly adjusted
closes. Reads data/prices_1mo.parquet (built by fetch_prices.py).

Rules (parameterised):
  * At the end of year Y-1, rank eligible stocks by their year Y-1 return and
    pick the top `--top` name(s), equal-weighted.
  * Hold through year Y. Return = Dec(Y) / Dec(Y-1) - 1 per name.
  * Optional stop-loss: if a held name's monthly close falls `--stop`% below the
    entry (Dec(Y-1)) price, exit at that close and sit in CASH until next Jan.
  * Eligibility at selection: has Dec(Y-1) and Dec(Y-2) closes, Dec(Y-1) price
    >= --min-price, and (optionally) flagged a common stock.

CAVEAT printed loudly: the universe is current listings only -> survivorship
bias inflates results. This is an upper bound, not truth.

Usage:
  python backtest.py [--start 2012] [--end 2026] [--stop 35] [--top 1]
                     [--min-price 5] [--common-only] [--no-stop]
"""
import argparse
import json
import os
import sys
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
RESULTS = os.path.join(HERE, "..", "results")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"


def year_end_prices(prices: pd.DataFrame) -> pd.DataFrame:
    """Pivot to a [year x ticker] table of each year's LAST monthly close."""
    p = prices.copy()
    p["date"] = pd.to_datetime(p["date"])
    p["year"] = p["date"].dt.year
    last = (p.sort_values("date")
              .groupby(["ticker", "year"], as_index=False)
              .last())
    return last.pivot(index="year", columns="ticker", values="close")


def load_benchmark(start: int, end: int) -> pd.Series:
    """S&P 500 (^GSPC) year-end closes, cached."""
    cache = os.path.join(DATA, "benchmark_gspc_1mo.parquet")
    if os.path.exists(cache):
        b = pd.read_parquet(cache)
    else:
        url = ("https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
               "?interval=1mo&range=max")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        res = d["chart"]["result"][0]
        dates = pd.to_datetime(res["timestamp"], unit="s").normalize()
        adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
        close = adj if adj is not None else res["indicators"]["quote"][0]["close"]
        b = pd.DataFrame({"date": dates, "close": close}).dropna()
        b.to_parquet(cache, index=False)
    b["date"] = pd.to_datetime(b["date"])
    b["year"] = b["date"].dt.year
    ye = b.sort_values("date").groupby("year")["close"].last()
    return ye


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1).min())


def cagr(equity: pd.Series, years: int) -> float:
    if years <= 0 or equity.iloc[0] <= 0:
        return float("nan")
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def run(args):
    prices = pd.read_parquet(os.path.join(DATA, "prices_1mo.parquet"))
    yep = year_end_prices(prices)

    common = None
    if args.common_only:
        uni = pd.read_csv(os.path.join(DATA, "universe.csv"))
        common = set(uni.loc[uni["is_common_guess"] == 1, "symbol"])

    # Monthly closes indexed by (ticker)->Series for intra-year stop checks.
    pm = prices.copy()
    pm["date"] = pd.to_datetime(pm["date"])
    pm["year"] = pm["date"].dt.year

    stop_frac = None if args.no_stop else (1 - args.stop / 100.0)

    rows = []
    equity = 1.0
    for Y in range(args.start, args.end + 1):
        if (Y - 2) not in yep.index or (Y - 1) not in yep.index:
            continue
        prev, prev2 = yep.loc[Y - 1], yep.loc[Y - 2]
        # eligibility
        elig = prev.dropna().index.intersection(prev2.dropna().index)
        cand = []
        for t in elig:
            if prev[t] < args.min_price:
                continue
            if common is not None and t not in common:
                continue
            r_prev = prev[t] / prev2[t] - 1
            cand.append((t, r_prev, prev[t]))
        if not cand:
            continue
        cand.sort(key=lambda x: x[1], reverse=True)
        picks = cand[:args.top]

        # realized return of the equal-weighted basket during year Y
        leg_rets = []
        detail = []
        for t, r_prev, entry in picks:
            have_Y = Y in yep.index and t in yep.columns and pd.notna(yep.loc[Y, t])
            if not have_Y:
                leg_rets.append(0.0)  # delisted mid-year -> treat as flat (optimistic)
                detail.append(f"{t}(+{r_prev*100:.0f}%->NA)")
                continue
            realized = yep.loc[Y, t] / entry - 1
            stopped = False
            if stop_frac is not None:
                yr = pm[(pm["ticker"] == t) & (pm["year"] == Y)].sort_values("date")
                for c in yr["close"]:
                    if c <= entry * stop_frac:
                        realized = c / entry - 1
                        stopped = True
                        break
            leg_rets.append(realized)
            detail.append(f"{t}(+{r_prev*100:.0f}%=>{realized*100:+.0f}%"
                          f"{'[STOP]' if stopped else ''})")

        yr_ret = sum(leg_rets) / len(leg_rets)
        equity *= (1 + yr_ret)
        rows.append({"year": Y, "picks": " ".join(detail),
                     "yr_ret": yr_ret, "equity": equity})

    strat = pd.DataFrame(rows).set_index("year")

    # benchmark aligned to same years
    bench_ye = load_benchmark(args.start, args.end)
    yrs = list(strat.index)
    base = bench_ye.get(yrs[0] - 1, bench_ye.get(yrs[0]))
    bench_eq = (bench_ye.reindex(yrs) / base)

    n = len(yrs)
    print("=" * 72)
    print("CHASING THE WINNER - P0 reproduction (monthly data)")
    print(f"start=${args.start_cash:.0f}  years {yrs[0]}..{yrs[-1]} ({n})  "
          f"top={args.top}  stop={'off' if args.no_stop else str(args.stop)+'%'}  "
          f"min_price=${args.min_price}  common_only={args.common_only}")
    print("!! universe = CURRENT listings only -> SURVIVORSHIP-BIASED (upper bound)")
    print("=" * 72)
    for Y in yrs:
        r = strat.loc[Y]
        print(f"{Y}: {r['yr_ret']*100:+7.1f}%  eq={r['equity']*args.start_cash:12,.0f}"
              f"   {r['picks']}")
    print("-" * 72)
    fin_strat = strat["equity"].iloc[-1] * args.start_cash
    fin_bench = bench_eq.iloc[-1] * args.start_cash
    print(f"FINAL  strategy: ${fin_strat:,.0f}   "
          f"CAGR {cagr(strat['equity'], n)*100:.1f}%   "
          f"maxDD {max_drawdown(strat['equity'])*100:.0f}%")
    print(f"FINAL  S&P 500 : ${fin_bench:,.0f}   "
          f"CAGR {cagr(bench_eq/bench_eq.iloc[0], n)*100:.1f}%   "
          f"maxDD {max_drawdown(bench_eq)*100:.0f}%")

    os.makedirs(RESULTS, exist_ok=True)
    tag = f"{yrs[0]}_{yrs[-1]}_top{args.top}_stop{'off' if args.no_stop else args.stop}"
    strat.to_csv(os.path.join(RESULTS, f"backtest_{tag}.csv"))
    print(f"\nsaved results/backtest_{tag}.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2012)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--stop", type=float, default=35.0)
    ap.add_argument("--no-stop", action="store_true")
    ap.add_argument("--top", type=int, default=1)
    ap.add_argument("--min-price", type=float, default=5.0)
    ap.add_argument("--common-only", action="store_true")
    ap.add_argument("--start-cash", type=float, default=100.0)
    run(ap.parse_args())
    return 0


if __name__ == "__main__":
    sys.exit(main())
