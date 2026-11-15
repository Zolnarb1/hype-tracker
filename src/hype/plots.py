"""Charts for the README (queries the DuckDB marts directly).  Usage:  python -m hype.plots"""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hype import DB_PATH, RESULTS_DIR

COL = {"game": "#4C78A8", "anime": "#E45756"}


def _clean(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def decay_chart(con):
    df = con.sql("""
        SELECT d.title, p.category, datediff('day', p.peak_day, d.day) AS t,
               d.views_7d / p.peak_views_7d AS share
        FROM fct_daily d JOIN dim_peak p USING (title)
        JOIN mart_decay m USING (title)
        WHERE d.day >= p.peak_day AND datediff('day', p.peak_day, d.day) <= 180
          AND m.days_observed >= 180
        ORDER BY d.title, t
    """).df()
    med = df.groupby(["category", "t"])["share"].median().reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    for (title, cat), g in df.groupby(["title", "category"]):
        ax.plot(g["t"], g["share"], color=COL[cat], alpha=0.12, lw=0.8)
    for cat, g in med.groupby("category"):
        ax.plot(g["t"], g["share"], color=COL[cat], lw=3, label={"game": "games", "anime": "anime"}[cat] + " (median)")
    ax.axhline(0.5, color="#999999", ls="--", lw=0.8)
    ax.text(178, 0.52, "half of peak", ha="right", fontsize=8, color="#777777")
    ax.set_xlabel("days after peak attention")
    ax.set_ylabel("7-day avg pageviews / peak")
    ax.set_ylim(0, 1.02)
    ax.set_title("How fast does hype fade? English Wikipedia pageviews, 36 games & anime",
                 loc="left", fontsize=11.5)
    ax.legend(frameon=False)
    _clean(ax)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "decay_curves.png", dpi=160)


def half_life_chart(con):
    df = con.sql("SELECT title, category, half_life_days FROM mart_decay "
                 "WHERE days_observed >= 365 ORDER BY half_life_days").df()
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.barh(df["title"], df["half_life_days"], color=[COL[c] for c in df["category"]])
    for i, v in enumerate(df["half_life_days"]):
        ax.text(v + 0.5, i, f"{v:.0f}", va="center", fontsize=8)
    ax.set_xlabel("days until attention halves after the peak")
    ax.set_title("Hype half-life (blue = game, red = anime)", loc="left", fontsize=11.5)
    ax.tick_params(axis="y", labelsize=8.5)
    _clean(ax)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "half_life.png", dpi=160)


def weekday_chart(con):
    df = con.table("mart_weekday").df()
    fig, ax = plt.subplots(figsize=(8, 4))
    for cat, g in df.groupby("category"):
        g = g.sort_values("dow")
        ax.plot(g["weekday"].str[:3], g["relative_views"], "-o", color=COL[cat], label=cat)
    ax.axhline(1, color="#999999", ls="--", lw=0.8)
    ax.set_ylabel("views vs. the title's weekly average")
    ax.set_title("Weekly rhythm (last 2 years)", loc="left", fontsize=11.5)
    ax.legend(frameon=False)
    _clean(ax)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "weekday.png", dpi=160)


if __name__ == "__main__":
    con = duckdb.connect(str(DB_PATH), read_only=True)
    decay_chart(con)
    half_life_chart(con)
    weekday_chart(con)
    print("charts saved to", RESULTS_DIR)
