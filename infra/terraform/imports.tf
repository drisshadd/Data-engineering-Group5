# Objects Member 1 already created by hand (2 Nov 2026). Terraform adopts them
# instead of trying to create them again (which would fail with "already exists").
# `terraform plan` shows them as "import", not "create". Nothing is dropped or recreated.
#
# Before the first plan, check in Snowsight what exists:
#   SHOW SCHEMAS IN DATABASE SKYHOP;   SHOW WAREHOUSES LIKE 'SKYHOP%';   SHOW ROLES LIKE 'SKYHOP%';
# If SILVER / GOLD / QUARANTINE, SKYHOP_TRANSFORM_WH or a SKYHOP_TRANSFORM / SKYHOP_ANALYST role
# already exist, uncomment the matching block below.

import {
  to = snowflake_database.skyhop
  id = "\"SKYHOP\""
}

import {
  to = snowflake_schema.layer["BRONZE"]
  id = "\"SKYHOP\".\"BRONZE\""
}

import {
  to = snowflake_warehouse.ingest
  id = "\"SKYHOP_WH\""
}

# import {
#   to = snowflake_schema.layer["SILVER"]
#   id = "\"SKYHOP\".\"SILVER\""
# }
# import {
#   to = snowflake_schema.layer["GOLD"]
#   id = "\"SKYHOP\".\"GOLD\""
# }
# import {
#   to = snowflake_schema.layer["QUARANTINE"]
#   id = "\"SKYHOP\".\"QUARANTINE\""
# }
# import {
#   to = snowflake_warehouse.transform
#   id = "\"SKYHOP_TRANSFORM_WH\""
# }
# import {
#   to = snowflake_account_role.analyst
#   id = "\"SKYHOP_ANALYST\""
# }
