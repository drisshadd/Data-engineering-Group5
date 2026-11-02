# Incident report — <short title>

Same format for all three incidents (copy this file to `docs/incidents/<member>_<incident>.md`).

| Field | Value |
|---|---|
| Owner | Member 1 / 2 / 3 |
| Date simulated | |
| Severity | Low / Medium / High (who would notice, how much money/data is wrong) |
| Detected by | test name / alert / dashboard check |
| Time to detect · to fix | |

## 1. What happened
One or two sentences, as a business user would say it ("revenue doubled overnight").

## 2. How we triggered it
Exact command or file change, so the panel can see it live.

## 3. How it was detected
Which check fired (dbt test, freshness, row-count gate, alert). Screenshot of the failure.

## 4. Impact
Which tables / dashboard tiles were wrong, how many rows, which batch. What did **not** get through.

## 5. Fix
What we ran. Why it is safe to rerun (idempotency: MERGE, PUT skip, watermark…).

## 6. Prevention
What now stops it from happening again, and what is still manual.

## 7. Evidence
Links to screenshots in `docs/evidence/`.
