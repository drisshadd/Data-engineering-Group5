-- =====================================================================================
-- 01 · BRONZE objects (Member 1). Run once with SYSADMIN (or the engineer role of Member 3).
-- Bronze rules: every column is TEXT, nothing is rejected, nothing is lost, every row knows its file and load time.
-- =====================================================================================
USE ROLE SYSADMIN;
USE WAREHOUSE SKYHOP_WH;
USE SCHEMA SKYHOP.BRONZE;

-- CSV read by header name: a new column in the source (schema drift) never shifts the others.
CREATE FILE FORMAT IF NOT EXISTS CSV_RAW
  TYPE = CSV PARSE_HEADER = TRUE FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE EMPTY_FIELD_AS_NULL = TRUE NULL_IF = ('') ENCODING = 'UTF8';

-- Internal stage (encrypted at rest by Snowflake). Folder convention written by the ingestion job:
--   flight_ops/batch_NNN/{flights,airports}.csv.gz        source 1 · flight-ops file drop
--   reservations/batch_NNN/{bookings,passengers}.csv.gz   source 2 · reservation DB (PostgreSQL extract)
CREATE STAGE IF NOT EXISTS LANDING DIRECTORY = (ENABLE = TRUE) COMMENT = 'SkyHop landing zone';

CREATE TABLE IF NOT EXISTS AIRPORTS (
  airport_code VARCHAR, city VARCHAR, runways VARCHAR,
  _source_file VARCHAR, _loaded_at TIMESTAMP_TZ);
CREATE TABLE IF NOT EXISTS FLIGHTS (
  flight_id VARCHAR, flight_number VARCHAR, origin VARCHAR, destination VARCHAR,
  scheduled_departure VARCHAR, delay_min VARCHAR, seats VARCHAR,
  _source_file VARCHAR, _loaded_at TIMESTAMP_TZ);
CREATE TABLE IF NOT EXISTS PASSENGERS (            -- PII: full_name, email (masking: Member 2 governance)
  passenger_id VARCHAR, full_name VARCHAR, email VARCHAR, frequent_flyer_tier VARCHAR,
  _source_file VARCHAR, _loaded_at TIMESTAMP_TZ);
-- booked_at_v2 + source_system = known schema drift of the reservation feed from batch 2 (both kept).
CREATE TABLE IF NOT EXISTS BOOKINGS (
  booking_id VARCHAR, flight_id VARCHAR, passenger_id VARCHAR, fare_gbp VARCHAR, cabin VARCHAR,
  booked_at VARCHAR, booked_at_v2 VARCHAR, source_system VARCHAR,
  _source_file VARCHAR, _loaded_at TIMESTAMP_TZ);

-- Public APIs: one JSON document per request, MERGEd on (source, request_key) -> re-pull never duplicates.
CREATE TABLE IF NOT EXISTS API_RAW (
  source VARCHAR, entity VARCHAR, request_key VARCHAR, payload VARIANT,
  _loaded_at TIMESTAMP_TZ DEFAULT CURRENT_TIMESTAMP());

-- Watermark of the incremental PostgreSQL extract (moved only after a successful COPY).
CREATE TABLE IF NOT EXISTS INGEST_WATERMARK (source VARCHAR, last_batch NUMBER, updated_at TIMESTAMP_TZ);

-- Reference seed (same as reference/city_reference.csv): city -> airport, coordinates, holiday calendar.
CREATE OR REPLACE TABLE CITY_REFERENCE (city VARCHAR, country VARCHAR, iata VARCHAR, latitude FLOAT, longitude FLOAT,
  holiday_calendar VARCHAR) AS
SELECT * FROM VALUES
  ('London','GB','LHR',51.4700,-0.4543,'england-and-wales'), ('Manchester','GB','MAN',53.3537,-2.2750,'england-and-wales'),
  ('Birmingham','GB','BHX',52.4539,-1.7480,'england-and-wales'), ('Leeds','GB','LBA',53.8659,-1.6606,'england-and-wales'),
  ('Glasgow','GB','GLA',55.8719,-4.4331,'scotland'), ('Bristol','GB','BRS',51.3827,-2.7191,'england-and-wales'),
  ('Liverpool','GB','LPL',53.3336,-2.8497,'england-and-wales'), ('Edinburgh','GB','EDI',55.9500,-3.3725,'scotland'),
  ('Cardiff','GB','CWL',51.3967,-3.3433,'england-and-wales'), ('Belfast','GB','BFS',54.6575,-6.2158,'northern-ireland'),
  ('Paris','FR','CDG',49.0097,2.5479,'FR'), ('Lyon','FR','LYS',45.7256,5.0811,'FR');

-- Ingestion service: write files, load bronze, merge API rows, move its watermark. Nothing else.
GRANT READ, WRITE ON STAGE SKYHOP.BRONZE.LANDING TO ROLE SKYHOP_INGEST;
GRANT USAGE ON FILE FORMAT SKYHOP.BRONZE.CSV_RAW TO ROLE SKYHOP_INGEST;
GRANT SELECT, INSERT ON TABLE SKYHOP.BRONZE.AIRPORTS   TO ROLE SKYHOP_INGEST;
GRANT SELECT, INSERT ON TABLE SKYHOP.BRONZE.FLIGHTS    TO ROLE SKYHOP_INGEST;
GRANT SELECT, INSERT ON TABLE SKYHOP.BRONZE.PASSENGERS TO ROLE SKYHOP_INGEST;
GRANT SELECT, INSERT ON TABLE SKYHOP.BRONZE.BOOKINGS   TO ROLE SKYHOP_INGEST;
GRANT SELECT, INSERT, UPDATE ON TABLE SKYHOP.BRONZE.API_RAW TO ROLE SKYHOP_INGEST;
GRANT SELECT, INSERT ON TABLE SKYHOP.BRONZE.INGEST_WATERMARK TO ROLE SKYHOP_INGEST;
GRANT SELECT ON TABLE SKYHOP.BRONZE.CITY_REFERENCE TO ROLE SKYHOP_INGEST;
