terraform {
  # 1.5+ is needed for the import blocks in imports.tf
  required_version = ">= 1.5.0"

  required_providers {
    snowflake = {
      source  = "snowflakedb/snowflake"
      version = "~> 2.22"
    }
  }

  # State stays local (terraform.tfstate, git-ignored). Keep a private backup copy
  # (OneDrive / Google Drive) after every apply: see docs/member3/MANUAL_STEPS.md.
}
