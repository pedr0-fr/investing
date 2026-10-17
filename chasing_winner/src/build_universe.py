"""Build the US-equity ticker universe for the Chasing-the-Winner backtest.

Source: rreichel3/US-Stock-Symbols (daily-refreshed mirror of the NASDAQ Trader
symbol directory for NASDAQ, NYSE and AMEX). This is a *current* snapshot of
listed symbols, so the resulting universe is SURVIVORSHIP-BIASED: names that
delisted/went to zero in the past are absent. We acquire everything now and
apply selection/liquidity filters at backtest time (not here), so the raw
dataset stays reusable.

Output: data/universe.csv  (one row per symbol + metadata + a crude
`is_common_guess` flag we can refine later without re-downloading prices).
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
EXCHANGES = ("nasdaq", "nyse", "amex")
BASE = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main"

# Name keywords that strongly suggest a non-common-stock instrument. Kept
# conservative: ADRs/ADSs are real equities and are NOT excluded.
NON_COMMON_KEYWORDS = (
    " etf", " etn", "exchange traded", "proshares", "ishares", "spdr",
    "index fund", " trust fund", "closed end", "closed-end", "warrant",
    " right ", " rights", " unit", " units", "preferred", "depositary shares",
    "% notes", "senior notes", "subordinated",
)


def fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def looks_common(symbol: str, name: str) -> bool:
    n = f" {name.lower()} "
    if any(k in n for k in NON_COMMON_KEYWORDS):
        return False
    # Warrant/unit/preferred share-class suffixes on the ticker itself.
    if any(c in symbol for c in (".", "^", "/", "$")):
        return False
    if len(symbol) == 5 and symbol[-1] in ("W", "R", "U", "P"):
        return False
    return True


def main() -> int:
    os.makedirs(DATA, exist_ok=True)
    rows, seen = [], set()
    for ex in EXCHANGES:
        url = f"{BASE}/{ex}/{ex}_full_tickers.json"
        print(f"fetching {url} ...", flush=True)
        for d in fetch_json(url):
            sym = (d.get("symbol") or "").strip().upper()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            name = (d.get("name") or "").strip()
            mcap = d.get("marketCap") or ""
            try:
                mcap_f = float(mcap)
            except (TypeError, ValueError):
                mcap_f = ""
            rows.append({
                "symbol": sym,
                "name": name,
                "exchange": ex,
                "sector": d.get("sector") or "",
                "industry": d.get("industry") or "",
                "country": d.get("country") or "",
                "ipoyear": d.get("ipoyear") or "",
                "marketCap": mcap_f,
                "is_common_guess": int(looks_common(sym, name)),
            })

    rows.sort(key=lambda r: r["symbol"])
    import csv
    out = os.path.join(DATA, "universe.csv")
    cols = ["symbol", "name", "exchange", "sector", "industry", "country",
            "ipoyear", "marketCap", "is_common_guess"]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    common = sum(r["is_common_guess"] for r in rows)
    print(f"\nwrote {out}")
    print(f"  total symbols:        {len(rows)}")
    print(f"  common-stock guess:   {common}")
    print(f"  excluded (ETF/etc.):  {len(rows) - common}")
    print("NOTE: current listings only -> survivorship-biased (documented).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
