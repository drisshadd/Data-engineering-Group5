# ---------------------------------------------------------------------------
# Roles
#   SKYHOP_INGEST    (exists, Member 1's snowflake/bronze/00_ingest_access.sql) - not managed here
#   SKYHOP_TRANSFORM (new) dbt: reads BRONZE, builds SILVER / GOLD / QUARANTINE
#   SKYHOP_ANALYST   (new) read-only on GOLD, used by the dashboard
# Both new roles roll up to SYSADMIN (Snowflake best practice: no orphan roles).
# ---------------------------------------------------------------------------
resource "snowflake_account_role" "transform" {
  provider = snowflake.securityadmin
  name     = "SKYHOP_TRANSFORM"
  comment  = "dbt (Member 2): read bronze, write silver/gold/quarantine"
}

resource "snowflake_account_role" "analyst" {
  provider = snowflake.securityadmin
  name     = "SKYHOP_ANALYST"
  comment  = "Read-only on SKYHOP.GOLD (dashboard, panel)"
}

resource "snowflake_grant_account_role" "transform_to_sysadmin" {
  provider         = snowflake.securityadmin
  role_name        = snowflake_account_role.transform.name
  parent_role_name = "SYSADMIN"
}

resource "snowflake_grant_account_role" "analyst_to_sysadmin" {
  provider         = snowflake.securityadmin
  role_name        = snowflake_account_role.analyst.name
  parent_role_name = "SYSADMIN"
}

# ---------------------------------------------------------------------------
# SKYHOP_TRANSFORM
# ---------------------------------------------------------------------------
resource "snowflake_grant_privileges_to_account_role" "transform_db" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.transform.name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.skyhop.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "transform_wh" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.transform.name
  privileges        = ["USAGE", "OPERATE"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.transform.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "transform_bronze_usage" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.transform.name
  privileges        = ["USAGE"]
  on_schema {
    schema_name = snowflake_schema.layer["BRONZE"].fully_qualified_name
  }
}

resource "snowflake_grant_privileges_to_account_role" "transform_bronze_all_tables" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.transform.name
  privileges        = ["SELECT"]
  on_schema_object {
    all {
      object_type_plural = "TABLES"
      in_schema          = snowflake_schema.layer["BRONZE"].fully_qualified_name
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "transform_bronze_future_tables" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.transform.name
  privileges        = ["SELECT"]
  on_schema_object {
    future {
      object_type_plural = "TABLES"
      in_schema          = snowflake_schema.layer["BRONZE"].fully_qualified_name
    }
  }
}

# dbt creates and owns its tables/views in these three schemas.
# CREATE MASKING POLICY: governance (mask passenger email / name) is done by dbt too.
resource "snowflake_grant_privileges_to_account_role" "transform_build_schemas" {
  for_each = toset(["SILVER", "GOLD", "QUARANTINE"])

  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.transform.name
  privileges        = ["USAGE", "CREATE TABLE", "CREATE VIEW", "CREATE MASKING POLICY"]
  on_schema {
    schema_name = snowflake_schema.layer[each.key].fully_qualified_name
  }
}

# ---------------------------------------------------------------------------
# SKYHOP_ANALYST: GOLD only, read only. Uses SKYHOP_WH (dashboard).
# ---------------------------------------------------------------------------
resource "snowflake_grant_privileges_to_account_role" "analyst_db" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.analyst.name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "DATABASE"
    object_name = snowflake_database.skyhop.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "analyst_wh" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.analyst.name
  privileges        = ["USAGE"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.ingest.name
  }
}

resource "snowflake_grant_privileges_to_account_role" "analyst_gold_usage" {
  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.analyst.name
  privileges        = ["USAGE"]
  on_schema {
    schema_name = snowflake_schema.layer["GOLD"].fully_qualified_name
  }
}

# Existing + future tables and views in GOLD, so whatever dbt builds tomorrow is readable.
# If "future" fails on your account, delete the analyst_gold_future block and re-grant by hand
# after dbt runs (GRANT SELECT ON ALL TABLES/VIEWS IN SCHEMA SKYHOP.GOLD TO ROLE SKYHOP_ANALYST).
resource "snowflake_grant_privileges_to_account_role" "analyst_gold_all" {
  for_each = toset(["TABLES", "VIEWS"])

  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.analyst.name
  privileges        = ["SELECT"]
  on_schema_object {
    all {
      object_type_plural = each.key
      in_schema          = snowflake_schema.layer["GOLD"].fully_qualified_name
    }
  }
}

resource "snowflake_grant_privileges_to_account_role" "analyst_gold_future" {
  for_each = toset(["TABLES", "VIEWS"])

  provider          = snowflake.securityadmin
  account_role_name = snowflake_account_role.analyst.name
  privileges        = ["SELECT"]
  on_schema_object {
    future {
      object_type_plural = each.key
      in_schema          = snowflake_schema.layer["GOLD"].fully_qualified_name
    }
  }
}
