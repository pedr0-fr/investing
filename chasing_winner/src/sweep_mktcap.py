"""Sweep: market-cap FLOOR x basket size for the overlapping momentum basket.

3 floors ({5,20,50}B, no upper bound) x 6 basket sizes (1..6) = 18 strategies.
Hold = 12 months, no stops, signal = trailing 12m return. Window 2012-2026.

Prints a markdown table (final $, CAGR, maxDD, rotations) and saves it to
results/sweep_mktcap.csv. Same survivorship/look-ahead caveat as P1.
"""
import argparse
import os
import types

import pandas as pd

import momentum_basket as mb

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2012)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--hold", type=int, default=12)
    ap.add_argument("--signal-lookback", type=int, default=12)
    ap.add_argument("--start-cash", type=float, default=100.0)
    a = ap.parse_args()

    floors = [5.0, 20.0, 50.0]
    sizes = [1, 2, 3, 4, 5, 6]

    panel = mb.load_panel()
    bench_raw = mb.load_benchmark()
    elig_cache = {f: mb.eligible_set(f, 1e12) for f in floors}  # 1e12 B = no cap

    rows = []
    for f in floors:
        for n in sizes:
            args = types.SimpleNamespace(
                n=n, hold=a.hold, signal_lookback=a.signal_lookback,
                mktcap_min=f, mktcap_max=1e12, min_price=5.0,
                start=a.start, end=a.end, start_cash=a.start_cash)
            equity, trades = mb.simulate(args, panel, elig_cache[f])
            rows.append({
                "floor_$B": int(f), "basket_n": n,
                "universe": len(elig_cache[f]),
                "final_$": equity.iloc[-1] * a.start_cash,
                "CAGR_%": mb.cagr(equity) * 100,
                "maxDD_%": mb.max_drawdown(equity) * 100,
                "rotations": len(trades) - 1,
            })

    bench = bench_raw.reindex(equity.index).ffill().bfill()
    bench = bench / bench.iloc[0]
    b_final = bench.iloc[-1] * a.start_cash
    b_cagr = mb.cagr(bench) * 100
    b_dd = mb.max_drawdown(bench) * 100

    df = pd.DataFrame(rows)
    os.makedirs(RESULTS, exist_ok=True)
    df.to_csv(os.path.join(RESULTS, "sweep_mktcap.csv"), index=False)

    print(f"\nOverlapping momentum basket | hold={a.hold}mo, no stop, "
          f"signal={a.signal_lookback}mo | {a.start}-{a.end} | ${a.start_cash:.0f} start")
    print("!! current listings + current mktcap -> survivorship/look-ahead bias\n")
    print("| mktcap floor | basket n | universe | final $ | CAGR % | maxDD % | rotations |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| ≥${r['floor_$B']}B | {r['basket_n']} | {r['universe']} | "
              f"${r['final_$']:,.0f} | {r['CAGR_%']:.1f} | {r['maxDD_%']:.0f} | "
              f"{r['rotations']} |")
    print(f"| **S&P 500** | - | - | **${b_final:,.0f}** | **{b_cagr:.1f}** | "
          f"**{b_dd:.0f}** | - |")
    print("\nsaved results/sweep_mktcap.csv")


if __name__ == "__main__":
    main()
