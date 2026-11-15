-- Hype decay after the peak.
--   half_life_days : days until the 7-day average first falls to half the peak
--   retention_30d / 90d / 365d : 7-day average N days after the peak, as a share of the peak
--   days_observed : how long after the peak we have data (recent peaks have less)
CREATE OR REPLACE TABLE mart_decay AS
WITH after_peak AS (
    SELECT d.title, d.day, d.views_7d, p.peak_day, p.peak_views_7d,
           datediff('day', p.peak_day, d.day) AS days_since_peak
    FROM fct_daily d
    JOIN dim_peak p USING (title)
    WHERE d.day >= p.peak_day
),
half AS (
    SELECT title, min(days_since_peak) AS half_life_days
    FROM after_peak
    WHERE views_7d <= 0.5 * peak_views_7d
    GROUP BY title
),
retention AS (
    SELECT title,
        max(CASE WHEN days_since_peak = 30  THEN views_7d / peak_views_7d END) AS retention_30d,
        max(CASE WHEN days_since_peak = 90  THEN views_7d / peak_views_7d END) AS retention_90d,
        max(CASE WHEN days_since_peak = 365 THEN views_7d / peak_views_7d END) AS retention_365d,
        max(days_since_peak) AS days_observed
    FROM after_peak
    GROUP BY title
)
SELECT p.title, p.category, p.peak_day, round(p.peak_views_7d) AS peak_views_7d,
       round(p.baseline_before) AS baseline_before,
       round(p.peak_views_7d / nullif(p.baseline_before, 0), 1) AS peak_vs_before,
       h.half_life_days, r.retention_30d, r.retention_90d, r.retention_365d, r.days_observed
FROM dim_peak p
LEFT JOIN half h USING (title)
LEFT JOIN retention r USING (title)
ORDER BY p.peak_views_7d DESC;
