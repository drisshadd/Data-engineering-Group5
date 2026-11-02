variable "snowflake_organization_name" {
  description = "First part of the account identifier: SELECT CURRENT_ORGANIZATION_NAME();"
  type        = string
}

variable "snowflake_account_name" {
  description = "Second part of the account identifier: SELECT CURRENT_ACCOUNT_NAME();"
  type        = string
}

variable "snowflake_user" {
  description = "Key-pair service user Terraform logs in with"
  type        = string
  default     = "TERRAFORM_SVC"
}

variable "snowflake_private_key_path" {
  description = "Path to the unencrypted PKCS#8 private key (.p8). Never commit it."
  type        = string
}

variable "database_name" {
  description = "Project database. Already created by Member 1, adopted via imports.tf"
  type        = string
  default     = "SKYHOP"
}

variable "warehouse_size" {
  type    = string
  default = "XSMALL"
}

variable "auto_suspend_seconds" {
  description = "Seconds of inactivity before a warehouse suspends (saves credits)"
  type        = number
  default     = 60
}
