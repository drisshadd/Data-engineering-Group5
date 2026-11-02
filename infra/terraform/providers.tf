# Least privilege: two roles, same key-pair service user (TERRAFORM_SVC, created in
# infra/snowflake/00_bootstrap_manual.sql).
#   SYSADMIN      -> owns the database, schemas and warehouses
#   SECURITYADMIN -> creates roles and grants (it has MANAGE GRANTS, needed for future grants)
# ACCOUNTADMIN is never used by Terraform. The credit limit (resource monitor) needs
# ACCOUNTADMIN, so it stays in the manual SQL.

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_user
  authenticator     = "SNOWFLAKE_JWT"
  private_key       = file(var.snowflake_private_key_path)
  role              = "SYSADMIN"
}

provider "snowflake" {
  alias             = "securityadmin"
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_user
  authenticator     = "SNOWFLAKE_JWT"
  private_key       = file(var.snowflake_private_key_path)
  role              = "SECURITYADMIN"
}
