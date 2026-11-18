"""The refresh gate must block broken extracts and let healthy ones through."""
import csv
from datetime import date

from hype.check import problems, summarise

TODAY = date(2026, 11, 18)


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["requested_title", "title", "category", "date", "views"])
        w.writerows(rows)


def test_healthy_extract_passes(tmp_path):
    write(tmp_path / "raw.csv", [["A", "A", "game", "20261116", 10], ["A", "A", "game", "20261117", 12],
                                 ["B", "B", "anime", "20261117", 5]])
    new = summarise(tmp_path / "raw.csv")
    old = {"rows": 2, "titles": ["A", "B"]}
    assert new["newest_day"] == "20261117"
    assert problems(new, old, TODAY, max_lag_days=4) == []


def test_blocks_missing_title_shrink_and_stale(tmp_path):
    write(tmp_path / "raw.csv", [["A", "A", "game", "20261001", 10]])
    new = summarise(tmp_path / "raw.csv")
    old = {"rows": 500, "titles": ["A", "B"]}
    found = " | ".join(problems(new, old, TODAY, max_lag_days=4))
    assert "titles disappeared: B" in found
    assert "extract shrank" in found
    assert "more than 4 days old" in found


def test_blocks_duplicates_and_negative_views(tmp_path):
    write(tmp_path / "raw.csv", [["A", "A", "game", "20261117", 10], ["A", "A", "game", "20261117", -1]])
    found = " | ".join(problems(summarise(tmp_path / "raw.csv"), None, TODAY, max_lag_days=4))
    assert "duplicate" in found and "negative" in found
