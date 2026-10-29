# Lab 2 grade — Jo_ella_Edwards

Status: **Proposed final — TA verification pending**

Score: **93/100**

## Task summary

- Task 1 — Infrastructure and security: **25/25**. Private networking, IAM, lifecycle, and LocalStack evidence met the requirements.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **17/20**. See deductions below.
- Task 4 — Written artifacts: **15/15**. Data contract and lineage diagram met the requirements; details below.
- Task 5 — Repository quality: **11/15**. See deductions below.

## Rubric breakdown

- **T3.4 — Feature job succeeded (-3):** The committed verifier says the latest feature-engineer run FAILED, feature Parquet was unreadable, and GetRecord returned no record. Evidence: docs/lab2-verify-output.txt:21; docs/lab2-verify-output.txt:29; docs/lab2-verify-output.txt:38
- **T5.3 — Terraform fmt and validate (-2):** The local terraform fmt check fails; the committed apply supports Terraform execution but does not establish clean formatting and validation. Evidence: infrastructure; docs/lab2-extend-output.txt; submitted validation log
- **T5.5 — README (-2):** The README has only a title and does not describe the new modules or how to run the pipeline. Evidence: README.md:1; README.md

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:10; docs/lab2-data-contract.md:13; docs/lab2-data-contract.md:27; docs/lab2-data-contract.md:36; docs/lab2-data-contract.md:39
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram includes the source, raw S3, crawler, catalog, transform, processed S3, feature job, feature S3, and Feature Store, with formats and write-role labels on the edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 0/2.** The README has only a title and does not describe the new modules or how to run the pipeline. Evidence: README.md:1

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.
- Committed verifier: 4 FAIL line(s) at docs/lab2-verify-output.txt:21, docs/lab2-verify-output.txt:29, docs/lab2-verify-output.txt:38, docs/lab2-verify-output.txt:54.
- FAIL-line review: The feature-job FAILED, unreadable Parquet, and empty GetRecord markers are reflected in T3.4; the other saved checks support the unaffected criteria.

## Canvas comment — draft; review before pasting

Great work Jo

The source covers the core pipeline, but the saved feature-job run failed and the local validation and README evidence are incomplete.

Few things missing:

- T3.4: The committed verifier says the latest feature-engineer run FAILED, feature Parquet was unreadable, and GetRecord returned no record. (-3 points)
- T5.3: The local terraform fmt check fails; the committed apply supports Terraform execution but does not establish clean formatting and validation. (-2 points)
- T5.5: The README has only a title and does not describe the new modules or how to run the pipeline. (-2 points)
