# Lab 2 LLM review

Use this procedure after the offline static grader produces a provisional report. Run the CLI for one named student directory per invocation. The reviewer reads submitted code and written work, records its judgments in `reviews/<student_id>.json`, and regenerates a proposed final score for TA verification. The Python CLI does not call an LLM API by itself; the Codex review step supplies the reasoning. The TA authorized Phase 5 grading of the 21 remaining students on 2026-10-20; the per-student procedure was repeated for that batch.

1. Run `grade_lab2.py` on one explicit child of the instructor `grading/lab2/` directory, or the approved `cs401r-jsims1/` checkout, with `--prepare-review`. This writes a provisional grade and `reviews/<student_id>.template.json` from the same static pass. The template contains candidate points, evidence, and flags, but leaves every LLM score blank. Do not invoke AWS, Terraform apply/destroy/init, student Python, or student shell scripts.
2. Read the student handout and `rubric_discrepancies.md` for scoring authority. For each of the 19 rubric rows, inspect the relevant Terraform/Python and any committed apply, verification, job, or teardown evidence. For submissions graded under the older Task 2 rubric provided by the TA, do not deduct for an absent `docs/lab2-verify-output.txt` on T2.1 or T2.4 alone: the older criteria did not require saving `get-table` or `get-job-run` output. T2.3 is limited to a Glue module whose apply creates the crawler and job without errors; do not deduct there solely for missing VPC connection or Terraform-managed uploads. Explicit saved FAIL evidence still counts. Check **every** `FAIL` line in any submitted verifier, regardless of a `0 failed` summary: older verifier copies omit data-quality failures from that count. A summary near 35 indicates an older or partial format; near 47 indicates the expanded format. Treat saved logs as historical claims supported by the submission, not live proof.
3. Read the complete data contract and visually inspect the lineage diagram. Judge the schema, grain, measurable guarantees, numeric SLA, versioning, required flow nodes, edge formats, and IAM role labels. Inspect Python semantics for transaction grain and temporal leakage; a structural match alone is insufficient.
4. Copy the template to `reviews/<student_id>.json`. Resolve **every** rubric item with a score, short reason, and precise file/line evidence. The script requires reasons and evidence for full credit too, and checks that the review belongs to the selected student. Static candidate points are hints, not final judgments. If evidence conflicts or is insufficient, leave the report provisional and describe what needs TA judgment. Check potential committed secrets without copying values into feedback. Use the handout's confirmed-secret zero and teardown cap only when supported.
5. Keep `review_type: "llm"` and `student_id` from the template. Set `reviewer`, `confirmed_secret`, and a concise, student-facing `canvas_summary`; use `review_notes` for evidence caveats the TA should see. If committed verification contains `FAIL` markers, resolve them in the affected rubric scores and set `verification_fail_reviewed: true` with a `verification_fail_reason`; otherwise the grade remains provisional. The summary appears before any rubric-coded deductions in the Canvas comment. Rerun `grade_lab2.py --review reviews/<student_id>.json` and inspect the generated grade and Canvas comment. The grade shows full-credit task summaries, only deducted rubric rows, and written-work reasons and evidence; the review JSON retains all 19 judgments. An incomplete LLM review is rejected instead of being labeled proposed final.
6. The output is a **proposed** score until the TA verifies it. Process another student only under the TA's current authorization. Never post a Canvas comment without explicit authorization.

Commands from `cs401r-mking38/`:

```bash
python3 grading/lab2/grade_lab2.py \
  ../cs401r-2026-instructor/grading/lab2/STUDENT_DIRECTORY \
  --prepare-review

# After completing reviews/STUDENT_DIRECTORY.json from the template:
python3 grading/lab2/grade_lab2.py \
  ../cs401r-2026-instructor/grading/lab2/STUDENT_DIRECTORY \
  --review grading/lab2/reviews/STUDENT_DIRECTORY.json
```
