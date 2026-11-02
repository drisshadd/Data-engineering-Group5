-- =====================================================================================
-- 00 · Ingestion access (Member 1). COORDINATE WITH MEMBER 3: if M3 already created the database, warehouse
-- and roles with Terraform, run only the lines that are missing. Role: ACCOUNTADMIN.
-- Expects: database SKYHOP, warehouse SKYHOP_WH (Member 3, Terraform).
-- =====================================================================================
USE ROLE ACCOUNTADMIN;
CREATE SCHEMA IF NOT EXISTS SKYHOP.BRONZE;
CREATE ROLE IF NOT EXISTS SKYHOP_INGEST;
GRANT USAGE ON WAREHOUSE SKYHOP_WH TO ROLE SKYHOP_INGEST;
GRANT USAGE ON DATABASE SKYHOP TO ROLE SKYHOP_INGEST;
GRANT USAGE ON SCHEMA SKYHOP.BRONZE TO ROLE SKYHOP_INGEST;

-- Service user for the ingestion container: key-pair only, no password.
-- On your Mac:  openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out keys/rsa_key.p8 -nocrypt
--               openssl rsa -in keys/rsa_key.p8 -pubout -out keys/rsa_key.pub
CREATE USER IF NOT EXISTS SKYHOP_INGEST_SVC TYPE = SERVICE DEFAULT_ROLE = SKYHOP_INGEST DEFAULT_WAREHOUSE = SKYHOP_WH
  COMMENT = 'SkyHop ingestion job (Member 1)';
-- ALTER USER SKYHOP_INGEST_SVC SET RSA_PUBLIC_KEY = '<body of keys/rsa_key.pub without BEGIN/END lines>';
GRANT ROLE SKYHOP_INGEST TO USER SKYHOP_INGEST_SVC;
GRANT ROLE SKYHOP_INGEST TO ROLE SYSADMIN;
-- Lets you (human) create bronze objects with your usual role:
GRANT ALL PRIVILEGES ON SCHEMA SKYHOP.BRONZE TO ROLE SYSADMIN;

-- Added 2 Nov 2026 after the live run: needed when SKYHOP / SKYHOP_WH were created by ACCOUNTADMIN
GRANT USAGE ON WAREHOUSE SKYHOP_WH TO ROLE SYSADMIN;
GRANT USAGE ON DATABASE SKYHOP TO ROLE SYSADMIN;
