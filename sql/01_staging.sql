-- Staging: typed, de-duplicated raw pageviews. One row per (title, day).
CREATE OR REPLACE TABLE stg_pageviews AS
SELECT
    title,
    any_value(category)                         AS category,
    strptime(CAST(date AS VARCHAR), '%Y%m%d')::DATE AS day,
    max(views)::BIGINT                          AS views
FROM read_csv_auto(getvariable('raw_csv'), header = true, types = {'date': 'VARCHAR'})
GROUP BY title, day;
