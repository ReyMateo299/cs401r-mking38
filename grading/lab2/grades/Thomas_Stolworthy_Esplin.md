# Lab 2 grade — Thomas_Stolworthy_Esplin

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

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:10; docs/lab2-data-contract.md:13; docs/lab2-data-contract.md:26; docs/lab2-data-contract.md:35; docs/lab2-data-contract.md:38
- **T4.2 — Lineage diagram: 7/7.** The visually inspected diagram includes the source, raw S3, crawler, catalog, transform, processed S3, feature job, feature S3, and Feature Store, with formats and write-role labels on the edges. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 2/2.** The README describes the Lab 2 modules and gives a usable end-to-end pipeline and verification sequence. Evidence: README.md

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.
- Review note: Git history contains LocalStack server.test.pem and server.test.pem.key files. They are local test certificates, not confirmed AWS credentials; no confirmed-secret override was applied. TA may verify their origin.
- Review note: TA regrade applies the no-saved-output rule to T3.4 as well: no deduction solely for the absent feature job-run file when the job is configured and apply completed; runtime status remains unverified offline.
- Potential security findings (values redacted): Git-history credential-like content: 00323b90bede9ef4e423231005810b4e0f0f8167:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 00323b90bede9ef4e423231005810b4e0f0f8167:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 0620e5b6b46044defdc29bef7697587354c1d812:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 0620e5b6b46044defdc29bef7697587354c1d812:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 1c5977240ca119a7086722827883b30f9c692f50:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 1c5977240ca119a7086722827883b30f9c692f50:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 51679692a8d72807547e14e89c4c9415f947171a:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 51679692a8d72807547e14e89c4c9415f947171a:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 817291e2dff0c4454cbeec3e4d366315031ca035:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 817291e2dff0c4454cbeec3e4d366315031ca035:.localstack/cache/server.test.pem.key (value redacted); …

## Canvas comment — draft; review before pasting

Great work Thomas

The submitted work meets the reviewed Lab 2 criteria.

