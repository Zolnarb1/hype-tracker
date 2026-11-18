"""Data-quality gate for the weekly refresh: refuse to publish a broken extract.

Run after ingest and before the SQL models. It compares the fresh raw extract with the
summary of the last published one (results/refresh.json) and fails (exit code 1) if:
  - a title that had data before has disappeared,
  - the extract shrank (fewer rows than last time: history should only grow),
  - the newest day is too old (the API is lagging or the download silently stopped early),
  - there are duplicate (title, day) rows or negative view counts.
On success it writes the new summary, which the refresh workflow commits with the results.

Usage:
    python -m hype.check [--max-lag-days 4]
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from hype import RAW_DIR, RESULTS_DIR


def summarise(raw_csv: Path) -> dict:
    rows, negatives, dupes = 0, 0, 0
    seen = set()
    last_day: dict[str, str] = defaultdict(str)
    with open(raw_csv, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows += 1
            key = (r["title"], r["date"])
            dupes += key in seen
            seen.add(key)
            negatives += int(r["views"]) < 0
            last_day[r["title"]] = max(last_day[r["title"]], r["date"])
    newest = max(last_day.values()) if last_day else ""
    return {"rows": rows, "titles": sorted(last_day), "newest_day": newest,
            "duplicates": dupes, "negative_views": negatives}


def problems(new: dict, old: dict | None, today: date, max_lag_days: int) -> list[str]:
    out = []
    if new["rows"] == 0:
        return ["extract is empty"]
    if new["duplicates"]:
        out.append(f"{new['duplicates']} duplicate (title, day) rows")
    if new["negative_views"]:
        out.append(f"{new['negative_views']} rows with negative views")
    newest = datetime.strptime(new["newest_day"], "%Y%m%d").date()
    if today - newest > timedelta(days=max_lag_days):
        out.append(f"newest day {newest} is more than {max_lag_days} days old")
    if old:
        missing = sorted(set(old["titles"]) - set(new["titles"]))
        if missing:
            out.append(f"titles disappeared: {', '.join(missing)}")
        if new["rows"] < old["rows"]:
            out.append(f"extract shrank: {new['rows']:,} rows vs {old['rows']:,} last time")
    return out


def main(max_lag_days: int) -> int:
    summary_path = RESULTS_DIR / "refresh.json"
    old = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
    new = summarise(RAW_DIR / "pageviews.csv")
    found = problems(new, old, date.today(), max_lag_days)
    if found:
        print("Data-quality check FAILED, results not refreshed:")
        for p in found:
            print(f"  - {p}")
        return 1
    new["refreshed_on"] = date.today().isoformat()
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(new, indent=1) + "\n", encoding="utf-8")
    grown = f" (+{new['rows'] - old['rows']:,} since last refresh)" if old else ""
    print(f"OK: {new['rows']:,} rows{grown}, {len(new['titles'])} titles, newest day {new['newest_day']}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--max-lag-days", type=int, default=4)
    sys.exit(main(p.parse_args().max_lag_days))
