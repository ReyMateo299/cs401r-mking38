# Lab 2 grade — XINWEI_ZHU

Status: **Proposed final — TA verification pending**

Score: **100/100**

## Task summary

- Task 1 — Infrastructure and security: **25/25**. Private networking, IAM, lifecycle, and LocalStack evidence met the requirements.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **15/15**. Data contract and lineage diagram met the requirements; details below.
- Task 5 — Repository quality: **15/15**. Terraform organization, validation, apply evidence, and README met the requirements.

## Rubric breakdown

No rubric deductions.

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:11; docs/lab2-data-contract.md:34; docs/lab2-data-contract.md:50; docs/lab2-data-contract.md:69; docs/lab2-data-contract.md:80
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram includes the source, raw S3, crawler, catalog, transform, processed S3, feature job, feature S3, and Feature Store, with formats and write-role labels on the edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 2/2.** The README describes the Lab 2 modules and gives a usable end-to-end pipeline and verification sequence. Evidence: README.md

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.

## Canvas comment — draft; review before pasting

Great work XINWEI

The submitted code and written work meet the reviewed Lab 2 criteria, and saved evidence supports the required pipeline results.

