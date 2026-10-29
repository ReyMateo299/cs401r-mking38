# Lab 2 grade — Sara_Beatriz_Hermosilla_Cifuentes

Status: **Proposed final — TA verification pending**

Score: **88/100**

## Task summary

- Task 1 — Infrastructure and security: **24/25**. See deductions below.
- Task 2 — Data catalog and ETL: **25/25**. Catalog, transform logic, and job evidence met the requirements.
- Task 3 — Features and Feature Store: **20/20**. Temporal features, Feature Group, and job evidence met the requirements.
- Task 4 — Written artifacts: **8/15**. See deductions below.
- Task 5 — Repository quality: **11/15**. See deductions below.

## Rubric breakdown

- **T1.1 — Private subnet, NAT, Domain (-1):** Private routing, NAT, and VpcOnly are present, but the security group has no self-referencing all-protocol ingress for private Glue worker communication. Evidence: infrastructure/modules/vpc/main.tf:82; infrastructure/modules/vpc/main.tf:105; infrastructure/modules/vpc/main.tf
- **T4.2 — Lineage diagram (-7):** The submitted PNG shows only the transform job; the required source-to-Feature-Store flow, formats, and IAM write roles are absent. Evidence: docs/lab2-data-lineage.png
- **T5.3 — Terraform fmt and validate (-2):** The local terraform fmt check fails; the successful committed apply does not satisfy the handout's clean fmt and validate criterion. Evidence: infrastructure; docs/lab2-extend-output.txt; submitted validation log
- **T5.5 — README (-2):** The README has only a title and no Lab 2 module or pipeline instructions. Evidence: README.md:1; README.md

## Written work review

- **T4.1 — Data contract: 8/8.** The contract identifies producer and consumers, states transaction grain, lists nine typed columns with nullability, at least three measurable guarantees, a two-hour freshness target, and a new-prefix/five-business-day breaking-change policy. Evidence: docs/lab2-data-contract.md:12; docs/lab2-data-contract.md:16; docs/lab2-data-contract.md:28; docs/lab2-data-contract.md:39; docs/lab2-data-contract.md:43
- **T4.2 — Lineage diagram: 0/7.** The submitted PNG shows only the transform job; the required source-to-Feature-Store flow, formats, and IAM write roles are absent. Evidence: docs/lab2-data-lineage.png
- **T5.5 — README: 0/2.** The README has only a title and no Lab 2 module or pipeline instructions. Evidence: README.md:1

## Overrides and evidence

- Teardown: present — default branch:docs/lab2-destroy-output.txt; committed destroy log ends in completion.
- Secret review: cleared.
- Rubric review: Codex LLM-assisted source, written-work, and submitted-evidence review; TA verification pending.
- Review note: Git history contains LocalStack server.test.pem and server.test.pem.key files. They are local test certificates, not confirmed AWS credentials; no confirmed-secret override was applied. TA may verify their origin.
- Review note: Applied the TA-supplied older Task 2.3 criterion: grade the Glue module and clean crawler/job apply; do not deduct this row for a private connection or separately committed script source.
- Potential security findings (values redacted): Git-history credential-like content: 354ef6cebc300e17d70cc6404f258799a9460700:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 354ef6cebc300e17d70cc6404f258799a9460700:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 615a5d5932e5a799f89b3de52a9a66b8d7e38ebd:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 615a5d5932e5a799f89b3de52a9a66b8d7e38ebd:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 7a0668da12f9465521d0fda69b4fcb7003367366:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 7a0668da12f9465521d0fda69b4fcb7003367366:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 7a6832323c674d591c52a18f8e00c5d16dfb3a00:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 7a6832323c674d591c52a18f8e00c5d16dfb3a00:.localstack/cache/server.test.pem.key (value redacted); Git-history credential-like content: 88e6a45d7cdefcb5e4ce30c376885ed003d1f887:.localstack/cache/server.test.pem (value redacted); Git-history credential-like content: 88e6a45d7cdefcb5e4ce30c376885ed003d1f887:.localstack/cache/server.test.pem.key (value redacted); …

## Canvas comment — draft; review before pasting

Great work Sara

I reviewed your Terraform, Python, written artifacts, and saved Lab 2 evidence. The deductions below identify the gaps found in the submitted work.

Few things missing:

- T1.1: Private routing, NAT, and VpcOnly are present, but the security group has no self-referencing all-protocol ingress for private Glue worker communication. (-1 points)
- T4.2: The submitted PNG shows only the transform job; the required source-to-Feature-Store flow, formats, and IAM write roles are absent. (-7 points)
- T5.3: The local terraform fmt check fails; the successful committed apply does not satisfy the handout's clean fmt and validate criterion. (-2 points)
- T5.5: The README has only a title and no Lab 2 module or pipeline instructions. (-2 points)
