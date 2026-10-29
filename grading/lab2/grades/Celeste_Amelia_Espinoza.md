# Lab 2 grade — Celeste_Amelia_Espinoza

Status: **Proposed final — TA verification pending**

Score: **87.5/100**

## Task summary

- Task 1 — Infrastructure and security: **12.5/25**. See deductions below.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **15/15**. Data contract and lineage diagram met the requirements; details below.
- Task 5 — Repository quality: **15/15**. Terraform organization, validation, apply evidence, and README met the requirements.

## Rubric breakdown

- **Teardown cap (-12.5):** Required post-submission evidence was not established; Task 1 is capped at 12.5/25.

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:19; docs/lab2-data-contract.md:24; docs/lab2-data-contract.md:39; docs/lab2-data-contract.md:73; docs/lab2-data-contract.md:79
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram includes the source, raw S3, crawler, catalog, transform, processed S3, feature job, feature S3, and Feature Store, with formats and write-role labels on the edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 2/2.** The README describes the Lab 2 modules and gives a usable end-to-end pipeline and verification sequence. Evidence: README.md

## Overrides and evidence

- Teardown: missing — TA review override.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.
- Review note: TA regrade applies the no-saved-output rule to T3.4 as well: no deduction solely for the absent feature job-run file when the job is configured and apply completed; runtime status remains unverified offline.

## Canvas comment — draft; review before pasting

Great work Celeste

The infrastructure and written artifacts cover much of the lab. The required post-submission teardown log is not present.

Few things missing:

- Teardown: Required post-submission evidence was not established; Task 1 is capped at 12.5/25 (-12.5 points)
