"""Transform + load: run the SQL models in sql/ (in file order) inside DuckDB.

Usage:
    python -m hype.pipeline
"""
import duckdb

from hype import DB_PATH, RAW_DIR, RESULTS_DIR, SQL_DIR


def run(con: duckdb.DuckDBPyConnection, raw_csv: str) -> None:
    con.execute("SET VARIABLE raw_csv = ?", [raw_csv])
    for path in sorted(SQL_DIR.glob("*.sql")):
        con.execute(path.read_text(encoding="utf-8"))
        print(f"  ran {path.name}")


def main() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    run(con, str(RAW_DIR / "pageviews.csv"))
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    for table in ("mart_decay", "mart_category", "mart_weekday"):
        df = con.table(table).df()
        df.to_csv(RESULTS_DIR / f"{table}.csv", index=False, float_format="%.3f")
    print(con.table("mart_category").df().to_string(index=False))
    print()
    print(con.sql("SELECT title, category, peak_day, peak_views_7d, half_life_days, "
                  "round(retention_90d, 3) AS ret_90d FROM mart_decay "
                  "WHERE days_observed >= 365 ORDER BY half_life_days").df().to_string(index=False))


if __name__ == "__main__":
    main()
