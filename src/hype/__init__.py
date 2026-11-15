"""Hype tracker: how fast does attention fade after a game or anime release? (DuckDB + SQL)"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "hype.duckdb"
SQL_DIR = ROOT / "sql"
RESULTS_DIR = ROOT / "results"
