-- Category comparison (only titles with at least a year of data after their peak).
CREATE OR REPLACE TABLE mart_category AS
SELECT category,
       count(*)                                  AS titles,
       median(half_life_days)                    AS median_half_life_days,
       round(median(retention_90d), 3)           AS median_retention_90d,
       round(median(retention_365d), 3)          AS median_retention_365d
FROM mart_decay
WHERE days_observed >= 365
GROUP BY category;

-- Weekly rhythm: average views per weekday, relative to each title's own weekly mean,
-- over the last 2 years (avoids launch spikes dominating).
CREATE OR REPLACE TABLE mart_weekday AS
WITH recent AS (
    SELECT title, category, day, views,
           avg(views) OVER (PARTITION BY title, date_trunc('week', day)) AS week_mean
    FROM fct_daily
    WHERE day >= (SELECT max(day) FROM fct_daily) - INTERVAL 730 DAY
)
SELECT category,
       dayname(day)                      AS weekday,
       isodow(day)                       AS dow,
       round(avg(views / nullif(week_mean, 0)), 3) AS relative_views
FROM recent
GROUP BY category, weekday, dow
ORDER BY category, dow;
