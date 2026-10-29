# Lab 2 grade — Gabriel_Santiago_Bolano_Petro

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

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:10; docs/lab2-data-contract.md:13; docs/lab2-data-contract.md:26; docs/lab2-data-contract.md:36; docs/lab2-data-contract.md:39
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram includes the source, raw S3, crawler, catalog, transform, processed S3, feature job, feature S3, and Feature Store, with formats and write-role labels on the edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 2/2.** The README describes the Lab 2 modules and gives a usable end-to-end pipeline and verification sequence. Evidence: README.md

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.

## Canvas comment — draft; review before pasting

Great work Gabriel

I reviewed your Terraform, Python, written artifacts, and saved Lab 2 evidence. The submitted work meets the reviewed rubric criteria.

