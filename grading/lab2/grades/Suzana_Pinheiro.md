# Lab 2 grade — Suzana_Pinheiro

Status: **Proposed final — TA verification pending**

Score: **87/100**

## Task summary

- Task 1 — Infrastructure and security: **17/25**. See deductions below.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **12/15**. See deductions below.
- Task 5 — Repository quality: **13/15**. See deductions below.

## Rubric breakdown

- **T1.2 — IAM roles and boundaries (-4):** All three roles exist, but MLEngineer can write processed/ and DataEngineer can write artifacts/glue/; those grants exceed the handout's required write boundaries. Evidence: infrastructure/modules/iam/main.tf:87; infrastructure/modules/iam/main.tf:168; infrastructure/modules/iam/main.tf:179
- **T1.3 — S3 lifecycle rules (-4):** Five lifecycle rules are present, but every retention period differs from the required 90/30/30/60/7-day values. Evidence: infrastructure/modules/storage/main.tf:68; infrastructure/modules/storage/main.tf:77; infrastructure/modules/storage/main.tf:90
- **T4.2 — Lineage diagram (-3):** The diagram includes the major source-to-Feature-Store nodes and CSV/Parquet/PutRecord labels, but none of its write edges identifies the IAM writer. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README (-2):** The README contains only a title, with no Lab 2 additions or run sequence. Evidence: README.md:1; README.md

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:10; docs/lab2-data-contract.md:13; docs/lab2-data-contract.md:26; docs/lab2-data-contract.md:32; docs/lab2-data-contract.md:35
- **T4.2 — Lineage diagram: 4/7.** The diagram includes the major source-to-Feature-Store nodes and CSV/Parquet/PutRecord labels, but none of its write edges identifies the IAM writer. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 0/2.** The README contains only a title, with no Lab 2 additions or run sequence. Evidence: README.md:1

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.
- Review note: Applied the TA-supplied older Task 2.3 criterion: grade the Glue module and clean crawler/job apply; do not deduct this row for a private connection or separately committed script source.
- Review note: TA regrade applies the no-saved-output rule to T3.4 as well: no deduction solely for the absent feature job-run file when the job is configured and apply completed; runtime status remains unverified offline.
- Review note: Restored the remaining T1.4 point because the LocalStack Terraform apply created all three IAM roles and the VPC with NAT disabled; the later awslocal verification could not run because awslocal was not installed.
- Review note: Restored the T1.1 point deducted for the missing self-referencing security-group ingress: the scored T1.1 criterion is private subnet, NAT, and Domain relocation, and the TA-supplied older Task 2.3 rubric excludes private Glue networking from that score.
- Review note: Regraded Task 2 and Task 3 after the Python sources were added. Static review awards full T2.2, T3.1, and T3.2 credit: types/date parsing, median and unknown imputation, transaction_id deduplication, fixed observation/outcome windows, customer-level RFM, tiers, bounded churn proxy, and outcome-derived label are implemented. T3.4 remains full under the TA no-saved-output ruling because the feature job is configured and the submitted apply completed; no AWS job was run as part of this regrade.
- Review note: Deployment follow-up: glue-scripts/transform.py and glue-scripts/feature_engineer.py are present, but infrastructure/modules/glue/main.tf references cs401r-lab2-template/glue-scripts/ for both source and filemd5. That directory is absent in the current repo; a fresh apply may fail or not use these newly added files. This is reported as implementation feedback and did not reduce the source-code rubric rows.

## Canvas comment — draft; review before pasting

Great work Suzana

The newly uploaded ETL scripts meet the source-level Task 2 and Task 3 requirements. Remaining deductions are for IAM boundaries, lifecycle durations, lineage labels, and README content.

Few things missing:

- T1.2: All three roles exist, but MLEngineer can write processed/ and DataEngineer can write artifacts/glue/; those grants exceed the handout's required write boundaries. (-4 points)
- T1.3: Five lifecycle rules are present, but every retention period differs from the required 90/30/30/60/7-day values. (-4 points)
- T4.2: The diagram includes the major source-to-Feature-Store nodes and CSV/Parquet/PutRecord labels, but none of its write edges identifies the IAM writer. (-3 points)
- T5.5: The README contains only a title, with no Lab 2 additions or run sequence. (-2 points)
