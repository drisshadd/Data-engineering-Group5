-- Read-only checks for Snowflake role owners; run in a worksheet with sufficient metadata visibility.
SHOW GRANTS ON SCHEMA SKYHOP.SILVER;
SHOW GRANTS ON SCHEMA SKYHOP.GOLD;
SHOW GRANTS ON SCHEMA SKYHOP.QUARANTINE;
SHOW GRANTS ON TABLE SKYHOP.SILVER.SILVER_PASSENGERS;
-- Do not claim PII isolation without reviewing the results and effective role inheritance.
