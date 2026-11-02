# Member 3 · Platform & Operations — Phase 1 checklist (Windows, Git Bash)

Goal tonight: the platform exists, so Member 1 and Member 2 are never blocked tomorrow.
Every step ends with a ✅ you can screenshot for the slides (`docs/evidence/member3/`).

> **Adapted to what Member 1 already did.** He created `SKYHOP`, `SKYHOP.BRONZE` and `SKYHOP_WH` by hand
> in his Snowflake account and loaded bronze. We keep that account and those names. Terraform **adopts**
> them (`infra/terraform/imports.tf`) instead of creating them again.

| # | Step | Who | Time | ✅ Check |
|---|---|---|---|---|
| 1 | Snowflake login in Member 1's account | M1 runs STEP 0 of the SQL | 5 min | you can log in to Snowsight |
| 2 | Inventory + ownership to SYSADMIN | you, STEP 1 | 5 min | `SHOW DATABASES LIKE 'SKYHOP'` owner = SYSADMIN |
| 3 | Key pair + `TERRAFORM_SVC` | you, STEP 2 | 15 min | `DESC USER TERRAFORM_SVC` shows `RSA_PUBLIC_KEY_FP` |
| 4 | Terraform | you | 30–45 min | 2nd `terraform plan` = **No changes** |
| 5 | Credit limit + team logins | you, STEPS 3–5 | 10 min | both warehouses show `SKYHOP_MONITOR`; analyst cannot read BRONZE |
| 6 | Docker check | you | 5 min | `docker run hello-world` |
| 7 | Team confirms names | all | 10 min | `PLATFORM_CONTRACT.md` 👍 from M1 and M2 |

## 1–3 · Snowflake (`infra/snowflake/00_bootstrap_manual.sql`)
Send Member 1 STEP 0 and ask him to run it (he owns the account). Then log in and run STEP 1 and STEP 2.
Keys go in `~/.snowflake/`, **never** inside the repo.

## 4 · Terraform
Install: `winget install Hashicorp.Terraform` (then reopen Git Bash) · `terraform -version` ≥ 1.5.
```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars   # fill org, account, key path (values from STEP 1)
terraform init
terraform fmt -check && terraform validate      # ✅ "Success! The configuration is valid."
terraform plan -out tfplan                      # read it, see below
terraform apply tfplan
terraform plan                                  # ✅ "No changes." -> no drift (screenshot)
```
What the first plan must say: **3 to import, ~23 to add, 0 to destroy**
(import = SKYHOP, SKYHOP.BRONZE, SKYHOP_WH; add = SILVER, GOLD, QUARANTINE, SKYHOP_TRANSFORM_WH,
2 roles and their grants). A `~ update in-place` on SKYHOP_WH is fine (size / auto-suspend aligned to 60 s).
**If the plan shows `destroy` or `-/+ replace` on anything: stop and don't apply.**

Common errors
- `JWT token is invalid` → wrong org/account in tfvars, or the public key was pasted with the BEGIN/END lines.
- `Object already exists` on SILVER/GOLD/... → uncomment the matching block in `imports.tf`.
- Errors only on `analyst_gold_future` → delete that block, apply, and grant by hand after dbt runs.
- `Insufficient privileges` on SKYHOP / SKYHOP_WH → STEP 1 ownership transfer was skipped.

State: `terraform.tfstate` stays on your laptop (git-ignored, it can contain secrets). After each apply copy it
to a private drive folder. Lose it = `terraform import` everything again.

## 5 · Finish the Snowflake setup
STEPS 3–5 of the SQL. Send Member 2 the `MEMBER2_DBT` login privately (not in the group chat), and put Member 1's
user name in the last grant of STEP 4.

## 6 · Docker (decides Phase 2)
```bash
docker run hello-world
```
- Works → Phase 2 = Airflow in Docker (`06-orchestration-and-docker/airflow/` from the course pack). Member 1's
  image is already there: `ingestion/Dockerfile`, commands listed in `docs/member1/HANDOVER_TO_M2.md` §5.
- Fails or slow → Snowflake Tasks (`snowflake-tasks/daily_pipeline_tasks.sql` in the pack). Don't spend hours on Docker.

## 7 · Team agreement
Post `docs/member3/PLATFORM_CONTRACT.md` in the group chat and get a 👍 from both tonight.

## Still manual (say it in the defence)
Account creation, user logins and passwords, key pairs, the credit limit, ownership transfer of the objects
Member 1 created before Terraform existed, and Terraform state backup. Everything else is code.
