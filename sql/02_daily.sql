-- Daily views with a 7-day rolling average (smooths the weekly cycle).
-- Days with no recorded views are filled with 0 so windows are calendar-correct.
CREATE OR REPLACE TABLE fct_daily AS
WITH bounds AS (
    SELECT title, any_value(category) AS category, min(day) AS first_day, max(day) AS last_day
    FROM stg_pageviews GROUP BY title
),
calendar AS (
    SELECT b.title, b.category, unnest(generate_series(b.first_day, b.last_day, INTERVAL 1 DAY))::DATE AS day
    FROM bounds b
)
SELECT
    c.title,
    c.category,
    c.day,
    coalesce(p.views, 0) AS views,
    avg(coalesce(p.views, 0)) OVER (
        PARTITION BY c.title ORDER BY c.day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS views_7d
FROM calendar c
LEFT JOIN stg_pageviews p USING (title, day);
