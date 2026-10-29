# Lab 2 grade — Madeline_Annette_Evans

Status: **Proposed final — TA verification pending**

Score: **92/100**

## Task summary

- Task 1 — Infrastructure and security: **25/25**. Private networking, IAM, lifecycle, and LocalStack evidence met the requirements.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **9/15**. See deductions below.
- Task 5 — Repository quality: **13/15**. See deductions below.

## Rubric breakdown

- **T4.1 — Data contract (-2):** The contract has typed schema and several measurable guarantees. Its 60-minute Glue timeout is not the requested two-hour raw-to-processed availability SLA, and its versioning text omits a new-prefix and five-business-day notice protocol. Evidence: docs/lab2-data-contract.md:20; docs/lab2-data-contract.md:70; docs/lab2-data-contract.md:87
- **T4.2 — Lineage diagram (-4):** The diagram traces source through raw, transform, processed, features and Feature Store, but combines crawler and catalog, omits formats on most arrows, and labels no IAM writer on the write edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README (-2):** The README contains only a title and no Lab 2 module or run instructions. Evidence: README.md:1; README.md

## Written work review

- **T4.1 — Data contract: 6/8.** The contract has typed schema and several measurable guarantees. Its 60-minute Glue timeout is not the requested two-hour raw-to-processed availability SLA, and its versioning text omits a new-prefix and five-business-day notice protocol. Evidence: docs/lab2-data-contract.md:20; docs/lab2-data-contract.md:70; docs/lab2-data-contract.md:87; docs/lab2-data-contract.md:106; docs/lab2-data-contract.md:63
- **T4.2 — Lineage diagram: 3/7.** The diagram traces source through raw, transform, processed, features and Feature Store, but combines crawler and catalog, omits formats on most arrows, and labels no IAM writer on the write edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 0/2.** The README contains only a title and no Lab 2 module or run instructions. Evidence: README.md:1

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.

## Canvas comment — draft; review before pasting

Great work Madeline

I reviewed your Terraform, Python, written artifacts, and saved Lab 2 evidence. The deductions below identify the gaps found in the submitted work.

Few things missing:

- T4.1: The contract has typed schema and several measurable guarantees. Its 60-minute Glue timeout is not the requested two-hour raw-to-processed availability SLA, and its versioning text omits a new-prefix and five-business-day notice protocol. (-2 points)
- T4.2: The diagram traces source through raw, transform, processed, features and Feature Store, but combines crawler and catalog, omits formats on most arrows, and labels no IAM writer on the write edges. (-4 points)
- T5.5: The README contains only a title and no Lab 2 module or run instructions. (-2 points)
