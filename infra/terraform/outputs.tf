output "database" {
  value = snowflake_database.skyhop.name
}

output "schemas" {
  value = [for s in snowflake_schema.layer : s.fully_qualified_name]
}

output "warehouses" {
  value = {
    ingest_and_dashboard = snowflake_warehouse.ingest.name
    dbt                  = snowflake_warehouse.transform.name
  }
}

output "roles" {
  value = {
    dbt     = snowflake_account_role.transform.name
    analyst = snowflake_account_role.analyst.name
  }
}
