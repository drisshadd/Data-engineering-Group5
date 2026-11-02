# ---------------------------------------------------------------------------
# Database and medallion schemas
# SKYHOP and SKYHOP.BRONZE already exist (Member 1 created them by hand on 2 Nov):
# imports.tf adopts them, Terraform creates the rest.
# ---------------------------------------------------------------------------
resource "snowflake_database" "skyhop" {
  name         = var.database_name
  is_transient = false # set explicitly so the import shows no diff
  comment      = "SkyHop airline data platform (Group 5). Managed by Terraform."
}

locals {
  schemas = {
    BRONZE     = "Raw data exactly as received (Member 1). Every column TEXT."
    SILVER     = "Cleaned, typed, deduplicated (Member 2, dbt)."
    GOLD       = "Business tables for the dashboard (Member 2, dbt). Analysts read only this."
    QUARANTINE = "Rows rejected by silver rules, with the reason (Member 2, dbt)."
  }
}

resource "snowflake_schema" "layer" {
  for_each = local.schemas

  database            = snowflake_database.skyhop.name
  name                = each.key
  comment             = each.value
  is_transient        = "false" # explicit, see import note in the provider docs
  with_managed_access = "false"
}

# ---------------------------------------------------------------------------
# Warehouses: X-Small, suspend after 60 s, resume on demand.
# SKYHOP_WH already exists (Member 1) -> imported. Used by ingestion + dashboard.
# SKYHOP_TRANSFORM_WH is new -> dbt only, so transformation cost is visible apart.
# The credit limit (resource monitor) is attached by hand as ACCOUNTADMIN, so
# Terraform must not try to remove it: ignore_changes.
# ---------------------------------------------------------------------------
resource "snowflake_warehouse" "ingest" {
  name                = "SKYHOP_WH"
  warehouse_size      = var.warehouse_size
  auto_suspend        = var.auto_suspend_seconds
  auto_resume         = "true"
  initially_suspended = true
  comment             = "Ingestion jobs + dashboard (Member 1). Managed by Terraform."

  lifecycle {
    ignore_changes = [resource_monitor, initially_suspended]
  }
}

resource "snowflake_warehouse" "transform" {
  name                = "SKYHOP_TRANSFORM_WH"
  warehouse_size      = var.warehouse_size
  auto_suspend        = var.auto_suspend_seconds
  auto_resume         = "true"
  initially_suspended = true
  comment             = "dbt builds and tests (Member 2). Managed by Terraform."

  lifecycle {
    ignore_changes = [resource_monitor, initially_suspended]
  }
}
