# Lab 2 grade — Matthew_King

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

- **T4.1 — Data contract: 8/8.** The contract names the producer and consumers, states transaction grain, documents nine typed columns with nullability, lists measurable quality guarantees, commits to a two-hour availability SLA, and specifies a new prefix plus five-business-day notice for breaking changes. Evidence: docs/lab2-data-contract.md:3; docs/lab2-data-contract.md:9; docs/lab2-data-contract.md:13; docs/lab2-data-contract.md:26; docs/lab2-data-contract.md:35; docs/lab2-data-contract.md:38
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram shows source to raw S3, crawler and catalog, transform to processed Parquet, feature job to feature Parquet and Feature Store, with formats and DataEngineer read/write labels on the edges. Editable draw.io source is included. Evidence: docs/lab2-data-lineage.png; docs/lab2-data-lineage.drawio
- **T5.5 — README: 2/2.** The README describes the Lab 2 modules, data flow, setup, run sequence, verification, and submitted documentation. Evidence: README.md:31; README.md:60; README.md:120

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; clean teardown verification in docs/lab2-teardown-verify-output.txt.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted rubric review; TA verification pending.
- Review note: The lab2-submit destroy log reports zero objects destroyed; the later default-branch teardown verification reports no billable Lab 2 resources. This supports the handout's teardown requirement, but the submitted evidence does not show how the deployed resources were removed.

## Canvas comment — draft; review before pasting

Great work Matthew

Your submitted code and saved verification output meet the Lab 2 infrastructure, ETL, feature engineering, and Feature Store requirements. The data contract and lineage diagram cover the written criteria, and the post-submission teardown verification reports no billable Lab 2 resources remaining.

