-- =====================================================================================
-- 00 · One-time manual setup (Member 3). Everything Terraform cannot or should not do.
-- Account = the one Member 1 already uses (SKYHOP + SKYHOP_WH + bronze live there).
-- Run block by block in a Snowsight worksheet, role ACCOUNTADMIN.
-- Order:  STEP 0 (Member 1) -> STEP 1-2 (Member 3) -> terraform apply -> STEP 3-5 (Member 3)
-- =====================================================================================

-- -------------------------------------------------------------------------------------
-- STEP 0 · Run by MEMBER 1 (account owner): give Member 3 an admin login.
-- -------------------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
CREATE USER IF NOT EXISTS GHITA_M3
  PASSWORD = '<temporary password, send it privately>'
  MUST_CHANGE_PASSWORD = TRUE
  DEFAULT_ROLE = SYSADMIN
  DEFAULT_WAREHOUSE = SKYHOP_WH
  COMMENT = 'Member 3 - platform (Terraform, orchestration, alerting)';
GRANT ROLE ACCOUNTADMIN TO USER GHITA_M3;   -- needed once for steps 1-5 (credit limit, ownership)
GRANT ROLE SYSADMIN     TO USER GHITA_M3;
GRANT ROLE SECURITYADMIN TO USER GHITA_M3;

-- -------------------------------------------------------------------------------------
-- STEP 1 · Member 3. Inventory: what does Member 1's setup look like? (screenshot it)
-- -------------------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
SELECT CURRENT_ORGANIZATION_NAME() AS org, CURRENT_ACCOUNT_NAME() AS account;  -- -> terraform.tfvars
SHOW DATABASES  LIKE 'SKYHOP';          -- column "owner"
SHOW SCHEMAS    IN DATABASE SKYHOP;
SHOW WAREHOUSES LIKE 'SKYHOP%';
SHOW ROLES      LIKE 'SKYHOP%';

-- Member 1 created SKYHOP / SKYHOP_WH as ACCOUNTADMIN. Hand them to SYSADMIN so Terraform
-- (which never uses ACCOUNTADMIN) can manage them. COPY CURRENT GRANTS keeps SKYHOP_INGEST's access,
-- so Member 1's ingestion keeps working. Harmless if SYSADMIN already owns them.
GRANT OWNERSHIP ON DATABASE  SKYHOP        TO ROLE SYSADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA    SKYHOP.BRONZE TO ROLE SYSADMIN COPY CURRENT GRANTS;
GRANT OWNERSHIP ON WAREHOUSE SKYHOP_WH     TO ROLE SYSADMIN COPY CURRENT GRANTS;

-- -------------------------------------------------------------------------------------
-- STEP 2 · Member 3. Terraform service user (key pair only, no password).
-- On your laptop (Git Bash on Windows):
--   mkdir -p ~/.snowflake
--   openssl genrsa 2048 | openssl pkcs8 -topk8 -inform PEM -out ~/.snowflake/terraform_key.p8 -nocrypt
--   openssl rsa -in ~/.snowflake/terraform_key.p8 -pubout -out ~/.snowflake/terraform_key.pub
-- Paste the body of terraform_key.pub (without the BEGIN/END lines, on one line) below.
-- -------------------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
CREATE USER IF NOT EXISTS TERRAFORM_SVC
  TYPE = SERVICE
  DEFAULT_ROLE = SYSADMIN
  COMMENT = 'Terraform (Member 3). Key-pair only.';
ALTER USER TERRAFORM_SVC SET RSA_PUBLIC_KEY = '<paste terraform_key.pub body here>';
GRANT ROLE SYSADMIN      TO USER TERRAFORM_SVC;
GRANT ROLE SECURITYADMIN TO USER TERRAFORM_SVC;
DESC USER TERRAFORM_SVC;   -- RSA_PUBLIC_KEY_FP must be filled in

-- ===================== now run terraform init / plan / apply ==========================

-- -------------------------------------------------------------------------------------
-- STEP 3 · Member 3. Credit limit (needs ACCOUNTADMIN, so not in Terraform).
-- Trial = 400 USD of credits; 20 credits/month is plenty for this project.
-- -------------------------------------------------------------------------------------
USE ROLE ACCOUNTADMIN;
CREATE RESOURCE MONITOR IF NOT EXISTS SKYHOP_MONITOR
  WITH CREDIT_QUOTA = 20
       FREQUENCY = MONTHLY
       START_TIMESTAMP = IMMEDIATELY
  TRIGGERS ON 75  PERCENT DO NOTIFY
           ON 100 PERCENT DO SUSPEND
           ON 110 PERCENT DO SUSPEND_IMMEDIATE;
ALTER WAREHOUSE SKYHOP_WH           SET RESOURCE_MONITOR = SKYHOP_MONITOR;
ALTER WAREHOUSE SKYHOP_TRANSFORM_WH SET RESOURCE_MONITOR = SKYHOP_MONITOR;
SHOW WAREHOUSES LIKE 'SKYHOP%';     -- column resource_monitor = SKYHOP_MONITOR on both

-- -------------------------------------------------------------------------------------
-- STEP 4 · Member 3. Login for Member 2 (dbt) + roles for the team.
-- -------------------------------------------------------------------------------------
USE ROLE SECURITYADMIN;
CREATE USER IF NOT EXISTS MEMBER2_DBT
  PASSWORD = '<temporary password, send it privately>'
  MUST_CHANGE_PASSWORD = TRUE
  DEFAULT_ROLE = SKYHOP_TRANSFORM
  DEFAULT_WAREHOUSE = SKYHOP_TRANSFORM_WH
  DEFAULT_NAMESPACE = SKYHOP.SILVER
  COMMENT = 'Member 2 - dbt (silver, gold, quality, governance)';
GRANT ROLE SKYHOP_TRANSFORM TO USER MEMBER2_DBT;
GRANT ROLE SKYHOP_ANALYST   TO USER MEMBER2_DBT;
-- Member 1 tests the dashboard as an analyst (replace with his user name: SELECT CURRENT_USER(); as him)
GRANT ROLE SKYHOP_ANALYST   TO USER <member1_user>;

-- -------------------------------------------------------------------------------------
-- STEP 5 · Member 3. Proof for the slides: the analyst role really is read-only on GOLD.
-- -------------------------------------------------------------------------------------
USE ROLE SKYHOP_ANALYST;
USE WAREHOUSE SKYHOP_WH;
SHOW SCHEMAS IN DATABASE SKYHOP;            -- only GOLD (and INFORMATION_SCHEMA) is visible
SELECT COUNT(*) FROM SKYHOP.BRONZE.FLIGHTS;  -- must FAIL: "does not exist or not authorized"

USE ROLE SKYHOP_TRANSFORM;
USE WAREHOUSE SKYHOP_TRANSFORM_WH;
SELECT COUNT(*) FROM SKYHOP.BRONZE.FLIGHTS;  -- must work (976 rows after Member 1's two batches)
