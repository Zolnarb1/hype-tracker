"""Extract: daily English-Wikipedia pageviews for each title in titles.csv.

1. Resolve each title to its canonical article (follows redirects) with the MediaWiki API.
2. Download daily pageviews (human traffic only, all devices) from the Wikimedia REST API.
3. Write one raw CSV per run: data/raw/pageviews.csv  (title, category, date, views).

APIs are free and public; Wikimedia asks clients to send a descriptive User-Agent and to
stay well under 100 requests/s (we do about 2/s).

Usage:
    python -m hype.ingest                      # 2020-01-01 .. yesterday
    python -m hype.ingest --start 2020-01-01 --end 2026-11-14
"""
import argparse
import csv
import json
import time
from datetime import date, timedelta
import urllib.error
import urllib.parse
import urllib.request

from hype import RAW_DIR, ROOT

UA = {"User-Agent": "hype-tracker-portfolio/0.1 (educational data-engineering project)"}
REST = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"


def _get(url: str, retries: int = 5) -> dict:
    """GET JSON; on HTTP 429 (rate limited) wait and retry with exponential back-off."""
    for attempt in range(retries):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == retries - 1:
                raise
            wait = float(e.headers.get("Retry-After") or 2 ** (attempt + 2))
            print(f"  rate limited, waiting {wait:.0f}s")
            time.sleep(wait)


def resolve(title: str) -> str | None:
    q = urllib.parse.urlencode({"action": "query", "titles": title, "redirects": 1,
                                "format": "json", "formatversion": 2})
    page = _get(f"https://en.wikipedia.org/w/api.php?{q}")["query"]["pages"][0]
    return None if page.get("missing") else page["title"]


def pageviews(title: str, start: str, end: str) -> list[dict]:
    article = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = f"{REST}/{article}/daily/{start.replace('-', '')}00/{end.replace('-', '')}00"
    try:
        return _get(url)["items"]
    except urllib.error.HTTPError as e:
        if e.code == 404:                  # no views recorded in the range
            return []
        raise


def main(start: str, end: str) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(ROOT / "titles.csv", encoding="utf-8") as f:
        titles = list(csv.DictReader(f))
    out = RAW_DIR / "pageviews.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["requested_title", "title", "category", "date", "views"])
        for row in titles:
            canonical = resolve(row["title"])
            time.sleep(1.0)
            if canonical is None:
                print(f"  skip (no article): {row['title']}")
                continue
            items = pageviews(canonical, start, end)
            time.sleep(1.0)
            for it in items:
                w.writerow([row["title"], canonical, row["category"], it["timestamp"][:8], it["views"]])
            print(f"  {canonical:55s} {len(items):5d} days")
    print(f"Saved {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2020-01-01")
    # pageviews are published with about a day of delay
    p.add_argument("--end", default=(date.today() - timedelta(days=1)).isoformat())
    a = p.parse_args()
    main(a.start, a.end)

