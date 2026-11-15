"""Run the real SQL models on a tiny synthetic dataset where the answers are known."""
import csv
from datetime import date, timedelta

import duckdb

from hype.pipeline import run


def write_csv(path, series):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["requested_title", "title", "category", "date", "views"])
        for title, cat, values in series:
            for i, v in enumerate(values):
                if v is None:            # simulate a missing day in the API output
                    continue
                d = date(2024, 1, 1) + timedelta(days=i)
                w.writerow([title, title, cat, d.strftime("%Y%m%d"), v])


def test_peak_half_life_and_gap_filling(tmp_path):
    # 200 days at 100 views, a 14-day plateau at 10,000, then back to 100
    values = [100] * 200 + [10_000] * 14 + [100] * 400
    values[50] = None                                   # one missing day -> filled with 0
    raw = tmp_path / "raw.csv"
    write_csv(raw, [("Test Game", "game", values)])

    con = duckdb.connect()
    run(con, str(raw))

    n_days = con.sql("SELECT count(*) FROM fct_daily").fetchone()[0]
    assert n_days == len(values)                        # missing day re-inserted
    assert con.sql("SELECT views FROM fct_daily WHERE day = DATE '2024-02-20'").fetchone()[0] == 0

    peak_day, peak = con.sql("SELECT peak_day, peak_views_7d FROM dim_peak").fetchone()
    assert peak == 10_000                               # 7 full days at 10,000
    assert peak_day == date(2024, 1, 1) + timedelta(days=206)   # first day the 7-day avg hits 10,000

    half_life = con.sql("SELECT half_life_days FROM mart_decay").fetchone()[0]
    # plateau ends on day 213; the 7-day avg drops below 5,000 when 4 of 7 days are back at 100
    assert half_life == 11


def test_categories_are_summarised_separately(tmp_path):
    raw = tmp_path / "raw.csv"
    spike = [10] * 30 + [1000] * 7 + [10] * 400
    write_csv(raw, [("A", "game", spike), ("B", "anime", spike)])
    con = duckdb.connect()
    run(con, str(raw))
    cats = dict(con.sql("SELECT category, titles FROM mart_category").fetchall())
    assert cats == {"game": 1, "anime": 1}
