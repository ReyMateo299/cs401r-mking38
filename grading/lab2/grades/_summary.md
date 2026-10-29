# Lab 2 remaining submissions — TA review index

All 21 grades below are **proposed** scores from offline static analysis plus Codex review of source, written work, diagrams, and committed evidence. Each linked report includes the deducted rubric items, written-work reasoning, and a draft Canvas comment. No live AWS checks were run, and no Canvas grades or comments were posted. Boston Sharp and Matthew King were graded earlier.

| Student | Proposed score | Teardown cap |
|---|---:|---|
| [Andrew Sabolsky](Andrew_Sabolsky.md) | 100/100 | No |
| [Caden Annison](Caden_Annison.md) | 100/100 | No |
| [Cameron James Chamberlain](Cameron_James_Chamberlain.md) | 98/100 | No |
| [Celeste Amelia Espinoza](Celeste_Amelia_Espinoza.md) | 87.5/100 | Yes |
| [Christian Mijangos Xicara](Christian_Mijangos_Xicara.md) | 100/100 | No |
| [Daniel Joseph Wright](Daniel_Joseph_Wright.md) | 100/100 | No |
| [Dawson Martin](Dawson_Martin.md) | 100/100 | No |
| [Gabriel Santiago Bolano Petro](Gabriel_Santiago_Bolano_Petro.md) | 100/100 | No |
| [Hayden Kyle Peterson](Hayden_Kyle_Peterson.md) | 100/100 | No |
| [Jared Cook Sims](Jared_Cook_Sims.md) | 100/100 | No |
| [Jo'ella Edwards](Jo_ella_Edwards.md) | 93/100 | No |
| [Joseph Dahlke](Joseph_Dahlke.md) | 100/100 | No |
| [Joseph Flanagan Gerard](Joseph_Flanagan_Gerard.md) | 100/100 | No |
| [Madeline Annette Evans](Madeline_Annette_Evans.md) | 92/100 | No |
| [Matthew Farnsworth](Matthew_Farnsworth.md) | 100/100 | No |
| [Ramez Jacob Khalil Gammoh](Ramez_Jacob_Khalil_Gammoh.md) | 100/100 | No |
| [Sara Beatriz Hermosilla Cifuentes](Sara_Beatriz_Hermosilla_Cifuentes.md) | 88/100 | No |
| [Suzana Pinheiro](Suzana_Pinheiro.md) | 87/100 | No |
| [Thomas Stolworthy Esplin](Thomas_Stolworthy_Esplin.md) | 100/100 | No |
| [Tyler Chartrand](Tyler_Chartrand.md) | 99/100 | No |
| [Xinwei Zhu](XINWEI_ZHU.md) | 100/100 | No |

## Items for TA attention

- **Teardown evidence:** The TA waived the `No billable Lab 2 resources remain` wording because the kit changed during the semester. A committed log ending in `Destroy complete!` now satisfies the offline completion gate. Only Celeste's report retains the Task 1 half-credit cap because no destroy log was found. The reports do not claim current AWS resource status.
- **Older Task 2 rubric applied:** The TA-provided version did not require saving `get-table` or `get-job-run` output. Six students regained 2 T2.1 points and 3 T2.4 points each; missing verifier output alone is not a deduction for those rows. Sara and Suzana also regained T2.3 points because their saved applies created the crawler and jobs cleanly; private networking and script-upload expectations are outside that older T2.3 criterion.
- **T2.2 grain wording:** The older table says “no duplicate `customer_id` rows,” but the applicable handout requires many transaction rows per customer and deduplication by `transaction_id`. The solution notes confirm the older customer-ID wording contradicts the grain and should not be deducted. Suzana's newly added `transform.py` now receives full T2.2 credit for transaction-ID deduplication.
- **T3.4 evidence:** By TA direction, the no-saved-output rule also applies to feature-job success. Cameron, Celeste, Christian, Jared, Suzana, and Thomas regained 3 points each when their job configuration and clean apply were present. Jo'ella retains the deduction because her submitted verifier explicitly reports a failed feature job and no returned record. Historical runtime success was not independently confirmed; no live AWS checks were run.
- **Saved verifier failures:** Jo'ella's log reports a failed feature job, unreadable feature Parquet, and empty GetRecord; the T3.4 deduction reflects these. Hayden's six documentation FAIL lines refer to contract and diagram files present at the submitted tag, so they were treated as stale.
- **Jo'ella LocalStack review:** Restored T1.4 (+3) because the submitted output stopped before Terraform ran (`terraform: not found`), while the local provider endpoint and shared-module configuration statically meet the LocalStack setup requirements. Kept T3.4 (-3): the verifier records an actual failed feature job and no feature Parquet, so source configuration alone does not satisfy the rubric's SUCCEEDED-status criterion.
- **Suzana re-review:** Restored 2 points on Task 1: T1.1 (+1), because self-referencing security-group ingress is not a scored component of the private-subnet/NAT/Domain criterion and private Glue networking is excluded by the older Task 2.3 rubric; and T1.4 (+1), because her successful LocalStack Terraform apply created three IAM roles and a VPC with NAT disabled, while only the follow-up `awslocal` check was blocked by the missing CLI. After the ETL scripts were added, restored T2.2 (+12), T3.1 (+10), and T3.2 (+4) based on static source review; no AWS jobs were run. Task 2 and Task 3 now score 25/25 and 20/20. Remaining deductions concern IAM boundaries, lifecycle durations, lineage role labels, and README content.
- **Suzana deployment note:** The uploaded scripts are under `glue-scripts/`, but `infrastructure/modules/glue/main.tf` still points its S3 object `source` and `filemd5` at `cs401r-lab2-template/glue-scripts/`. That path is absent in the current repo, so a fresh apply may not upload these newly graded scripts. This was recorded for TA follow-up and did not change the source-code rubric scores.
- **Security review:** Sara and Thomas have LocalStack `server.test.pem` and `server.test.pem.key` artifacts in Git history. They were treated as local test certificates, not confirmed AWS credentials; this is recorded for TA verification.
- **Encoded log:** Christian's extension apply log is UTF-16 and shows a successful 31-resource apply when decoded. The grader now recognizes UTF-16 files.

The completed row-by-row judgments are in `../reviews/<student_id>.json`. All reports are marked **Proposed final — TA verification pending**.
