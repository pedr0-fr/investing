"""Build an international large-cap universe from companiesmarketcap.com.

Free, no-key. Each country page lists companies by market cap (USD) with a
Yahoo-compatible ticker (local tickers carry the exchange suffix, e.g. 9984.T;
big names show their ADR, e.g. TM/MUFG — both resolve on Yahoo's chart API).

Keeps companies with market cap >= --min-cap (USD, default 10e9), across all
countries the site covers (ex-US by default — we already have a US panel).
Output: data/universe_intl.csv [ticker, name, country, marketCap].
"""
import argparse
import html
import os
import re
import time
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
BASE = "https://companiesmarketcap.com"


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=30) as r:
                return r.read().decode("utf-8", "replace")
        except Exception:
            time.sleep(2 * (attempt + 1))
    return ""


def country_pages():
    """Return [(slug, full_path)] from all-countries — URL patterns are
    irregular (e.g. .../largest-companies-in-the-uk-by-market-cap/)."""
    h = get(f"{BASE}/all-countries/")
    paths = sorted(set(re.findall(
        r'href="(/([a-z-]+)/largest-companies-in-[a-z-]+-by-market-cap/)"', h)))
    return [(slug, path) for (path, slug) in paths
            if slug not in ("usa", "european-union")]


def parse_page(h):
    rows = []
    for m in re.finditer(r'company-name">([^<]+)</div>', h):
        seg = h[m.end():m.end() + 500]
        code = re.search(r'company-code">(?:<span[^>]*></span>)?\s*([^<]+)</div>', seg)
        cap = re.search(r'data-sort="(\d{9,})"', seg)
        if code and cap:
            rows.append((code.group(1).strip(),
                         html.unescape(m.group(1).strip()),
                         int(cap.group(1))))
    return rows


def scrape_country(slug, path, min_cap, sleep):
    name = slug.replace("-", " ").title()
    collected, page = [], 1
    while page <= 10:
        url = f"{BASE}{path}"
        if page > 1:
            url += f"?page={page}"
        rows = parse_page(get(url))
        if not rows:
            break
        keep = [(t, nm, c) for (t, nm, c) in rows if c >= min_cap]
        collected += keep
        # sorted desc by cap: stop once a page drops below the threshold
        if rows[-1][2] < min_cap or len(rows) < 100:
            break
        page += 1
        time.sleep(sleep)
    return [(t, nm, name, c) for (t, nm, c) in collected]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-cap", type=float, default=10e9)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--only", nargs="+", default=None, help="limit to these slugs")
    args = ap.parse_args()

    pages = country_pages()
    if args.only:
        pages = [(s, p) for (s, p) in pages if s in args.only]
    print(f"countries: {len(pages)}", flush=True)
    allrows = []
    for i, (slug, path) in enumerate(pages, 1):
        rows = scrape_country(slug, path, args.min_cap, args.sleep)
        allrows += rows
        print(f"[{i}/{len(pages)}] {slug}: {len(rows)} >= ${args.min_cap/1e9:.0f}B",
              flush=True)
        time.sleep(args.sleep)

    df = pd.DataFrame(allrows, columns=["ticker", "name", "country", "marketCap"])
    # a company can appear under multiple countries / dual listings -> keep the
    # highest-cap row per ticker
    df = (df.sort_values("marketCap", ascending=False)
            .drop_duplicates("ticker").reset_index(drop=True))
    out = os.path.join(DATA, "universe_intl.csv")
    df.to_csv(out, index=False)
    print(f"\nwrote {out}  | {len(df)} unique tickers, "
          f"{df['country'].nunique()} countries")
    print(df["country"].value_counts().head(20).to_string())


if __name__ == "__main__":
    main()
