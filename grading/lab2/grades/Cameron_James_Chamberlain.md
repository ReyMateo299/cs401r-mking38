# Lab 2 grade — Cameron_James_Chamberlain

Status: **Proposed final — TA verification pending**

Score: **98/100**

## Task summary

- Task 1 — Infrastructure and security: **25/25**. Private networking, IAM, lifecycle, and LocalStack evidence met the requirements.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **15/15**. Data contract and lineage diagram met the requirements; details below.
- Task 5 — Repository quality: **13/15**. See deductions below.

## Rubric breakdown

- **T5.5 — README (-2):** The README is a general course overview; it does not describe the Lab 2 modules or an end-to-end run sequence. Evidence: README.md:29; README.md:71; README.md

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:13; docs/lab2-data-contract.md:19; docs/lab2-data-contract.md:33; docs/lab2-data-contract.md:43; docs/lab2-data-contract.md:47
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram includes the source, raw S3, crawler, catalog, transform, processed S3, feature job, feature S3, and Feature Store, with formats and write-role labels on the edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 0/2.** The README is a general course overview; it does not describe the Lab 2 modules or an end-to-end run sequence. Evidence: README.md:29; README.md:71

## Overrides and evidence

- Teardown: present — docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.
- Review note: TA regrade applies the no-saved-output rule to T3.4 as well: no deduction solely for the absent feature job-run file when the job is configured and apply completed; runtime status remains unverified offline.

## Canvas comment — draft; review before pasting

Great work Cameron

The Terraform and written artifacts cover much of the lab. The README lacks Lab 2 run instructions.

Few things missing:

- T5.5: The README is a general course overview; it does not describe the Lab 2 modules or an end-to-end run sequence. (-2 points)
