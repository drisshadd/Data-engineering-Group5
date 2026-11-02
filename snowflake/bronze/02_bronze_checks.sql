-- =====================================================================================
-- 02 · "Bronze finished" evidence (Member 1) — screenshot each result for the handover and the slides.
-- Expected values: docs/member1/bronze_expected_counts.json (13,749 rows in 8 files for seed 42, 2 batches).
-- =====================================================================================
USE ROLE SYSADMIN;
USE WAREHOUSE SKYHOP_WH;
USE SCHEMA SKYHOP.BRONZE;

-- 1. Files that traversed the stage
LIST @LANDING;

-- 2. Rows per file (must equal bronze_expected_counts.json)
SELECT 'AIRPORTS' AS tbl, _source_file, COUNT(*) AS n, MIN(_loaded_at) AS loaded_at FROM AIRPORTS GROUP BY 1, 2
UNION ALL SELECT 'FLIGHTS', _source_file, COUNT(*), MIN(_loaded_at) FROM FLIGHTS GROUP BY 1, 2
UNION ALL SELECT 'PASSENGERS', _source_file, COUNT(*), MIN(_loaded_at) FROM PASSENGERS GROUP BY 1, 2
UNION ALL SELECT 'BOOKINGS', _source_file, COUNT(*), MIN(_loaded_at) FROM BOOKINGS GROUP BY 1, 2
ORDER BY 2;

-- 3. Load history (status, rows, errors) for the last 7 days
SELECT table_name, file_name, status, row_count, row_parsed, first_error_message, last_load_time
FROM TABLE(SKYHOP.INFORMATION_SCHEMA.COPY_HISTORY(TABLE_NAME => 'SKYHOP.BRONZE.BOOKINGS', START_TIME => DATEADD('day', -7, CURRENT_TIMESTAMP())))
UNION ALL
SELECT table_name, file_name, status, row_count, row_parsed, first_error_message, last_load_time
FROM TABLE(SKYHOP.INFORMATION_SCHEMA.COPY_HISTORY(TABLE_NAME => 'SKYHOP.BRONZE.FLIGHTS', START_TIME => DATEADD('day', -7, CURRENT_TIMESTAMP())))
ORDER BY last_load_time DESC;

-- 4. Schema drift captured: batch 2 bookings use booked_at_v2 + source_system, batch 1 uses booked_at
SELECT _source_file, COUNT(booked_at) AS booked_at_filled, COUNT(booked_at_v2) AS booked_at_v2_filled,
       COUNT(source_system) AS source_system_filled
FROM BOOKINGS GROUP BY 1 ORDER BY 1;

-- 5. API documents (one per request) and a peek inside each
SELECT source, COUNT(*) AS documents, MAX(_loaded_at) AS last_pull FROM API_RAW GROUP BY 1 ORDER BY 1;
SELECT entity, ARRAY_SIZE(payload:daily:time) AS days, payload:daily:precipitation_sum[0]::FLOAT AS first_day_rain_mm
FROM API_RAW WHERE source = 'open_meteo' ORDER BY entity;
SELECT COUNT(*) AS fx_days FROM API_RAW r, LATERAL FLATTEN(input => r.payload:rates) WHERE r.source = 'frankfurter';

-- 6. Watermark of the PostgreSQL extract
SELECT * FROM INGEST_WATERMARK ORDER BY updated_at DESC;

-- 7. Replay proof (incident B, Member 1 part): run the ingestion of batch 1 again, then rerun query 2.
--    Expected: PUT status SKIPPED, COPY "0 files processed", counts unchanged.
