# Lab 2 grade — Tyler_Chartrand

Status: **Proposed final — TA verification pending**

Score: **99/100**

## Task summary

- Task 1 — Infrastructure and security: **25/25**. Private networking, IAM, lifecycle, and LocalStack evidence met the requirements.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **14/15**. See deductions below.
- Task 5 — Repository quality: **15/15**. Terraform organization, validation, apply evidence, and README met the requirements.

## Rubric breakdown

- **T4.2 — Lineage diagram (-1):** The diagram shows the source, raw S3, Catalog, both jobs, both data outputs, and Feature Store with formats and writer roles, but omits the Glue Crawler as a distinct node. Evidence: docs/lab2-data-lineage.png

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:27; docs/lab2-data-contract.md:37; docs/lab2-data-contract.md:53; docs/lab2-data-contract.md:79; docs/lab2-data-contract.md:93
- **T4.2 — Lineage diagram: 6/7.** The diagram shows the source, raw S3, Catalog, both jobs, both data outputs, and Feature Store with formats and writer roles, but omits the Glue Crawler as a distinct node. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 2/2.** The README describes the Lab 2 modules and gives a usable end-to-end pipeline and verification sequence. Evidence: README.md

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.

## Canvas comment — draft; review before pasting

Great work Tyler

I reviewed your Terraform, Python, written artifacts, and saved Lab 2 evidence. The deductions below identify the gaps found in the submitted work.

Few things missing:

- T4.2: The diagram shows the source, raw S3, Catalog, both jobs, both data outputs, and Feature Store with formats and writer roles, but omits the Glue Crawler as a distinct node. (-1 points)
