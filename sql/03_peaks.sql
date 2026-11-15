-- Peak attention per title: the day with the highest 7-day average,
-- and the "before" level: median 7-day average over the 90 days before the climb.
CREATE OR REPLACE TABLE dim_peak AS
WITH ranked AS (
    SELECT *, row_number() OVER (PARTITION BY title ORDER BY views_7d DESC, day) AS rk
    FROM fct_daily
)
SELECT
    r.title,
    r.category,
    r.day      AS peak_day,
    r.views_7d AS peak_views_7d,
    (SELECT median(d.views_7d) FROM fct_daily d
      WHERE d.title = r.title
        AND d.day BETWEEN r.day - INTERVAL 120 DAY AND r.day - INTERVAL 30 DAY) AS baseline_before
FROM ranked r
WHERE rk = 1;
