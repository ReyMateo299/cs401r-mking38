# Offline Lab 2 grader

This directory contains the Phase 3 pipeline. It analyzes **one** student repository at a time. It never contacts AWS, executes student Python or shell scripts, initializes Terraform, applies infrastructure, or runs the submitted `verify-lab2.sh`. Terraform and Python source are the primary evidence for defined resources and logic; committed logs are evidence of historical runs.

## Run one submission

From `cs401r-mking38/`:

```bash
python3 grading/lab2/grade_lab2.py \
  ../cs401r-2026-instructor/grading/lab2/STUDENT_DIRECTORY
```

The accepted input is one immediate child of `cs401r-2026-instructor/grading/lab2/` or the specifically approved `cs401r-jsims1/` checkout for Jared Cook Sims. The latter defaults to student ID `Jared_Cook_Sims`. Output goes to `grading/lab2/grades/<student_id>.md`. The CLI has no batch mode.

For Jared's repository, use `python3 grading/lab2/grade_lab2.py ../cs401r-jsims1 --prepare-review` from `cs401r-mking38/` when grading begins.

The first run creates a **provisional** grade with candidate task totals, deductions, written-work evidence, pending review items, and a draft Canvas comment. Asterisks mark written-work candidate scores that need review. The script does not turn unavailable AWS evidence into a false pass or a false fail.

## LLM reasoning step

Use `--prepare-review` on a single student to generate the provisional grade and `reviews/<student_id>.template.json` in one static pass. Follow [the single-student review protocol](llm_review_protocol.md): Codex inspects the source, saved evidence, data contract, and lineage diagram, then completes all 19 rubric rows in `reviews/<student_id>.json`. The CLI rejects a partial LLM review or one labeled for another student. It uses the completed file to produce the proposed final score and Canvas comment. This is an agent review step in the pipeline; `grade_lab2.py` does not make an LLM API request. The [Boston review file](reviews/Boston_Sharp.json) is an example for TA verification.

## Finalize after review

For a TA-only override, create a JSON file with scores for the pending rubric rows. Every deduction override needs a reason that can be used in the Canvas comment. For an LLM review, start with the generated template and fill **every** row, including reasons and evidence for full-credit rows. For example, a TA-only review could contain:

```json
{
  "scores": {
    "T2.2": {
      "score": 10,
      "reason": "Only ISO purchase dates are parsed; the alternate input format becomes null.",
      "evidence": ["glue-scripts/transform.py:48"]
    },
    "T4.1": {
      "score": 8,
      "reason": "Complete contract with measurable guarantees and numeric SLA."
    },
    "T4.2": {
      "score": 7,
      "reason": "All required nodes, formats, and IAM write roles are shown."
    }
  },
  "teardown_evidence": "present",
  "confirmed_secret": false,
  "reviewer": "Codex LLM-assisted rubric review; TA verification pending",
  "canvas_summary": "The submitted work meets the reviewed rubric criteria. Proposed score: 100/100, pending TA verification."
}
```

Use `"teardown_evidence": "missing"` only after checking the default branch for the post-tag destroy log. A committed log ending in `Destroy complete!` establishes completion for this gate; the TA waived the later `No billable Lab 2 resources remain` wording because the kit changed during the semester. A missing log caps Task 1 at **12.5/25**. Use `"confirmed_secret": true` only after a human confirms an actual committed secret; the handout then sets the assignment grade to **0/100**. The script reports potential matches without printing credential values. A prohibited filename alone is not confirmation of a secret.

```bash
python3 grading/lab2/grade_lab2.py \
  ../cs401r-2026-instructor/grading/lab2/STUDENT_DIRECTORY \
  --review grading/lab2/reviews/STUDENT_DIRECTORY.json
```

The output status becomes **Proposed final — TA verification pending** when a complete LLM review resolves every score-bearing item, the teardown gate, and any security flag. The grade document has five short task totals, a rubric breakdown containing **only deductions**, and a separate evidence-backed review of the data contract, lineage diagram, and README. The complete row-by-row audit stays in the review JSON. The draft `## Canvas comment` identifies each deduction by Lab 2 rubric code (`T1.1` through `T5.5`) and point amount.

## What the script checks

- Terraform resources, module placement and wiring, lifecycle rules, IAM policy signals, Feature Group definitions, and parameterized names.
- Python function structure and syntax, dates, transaction grain signals, RFM columns, fixed temporal cutoff, loyalty tiers, risk score, and outcome-based label signals.
- Committed LocalStack, apply, verification, validation, and teardown logs; data contract and diagram presence; README instructions.
- Every committed verifier `FAIL` marker, even when an older script reports `0 failed`; unresolved markers block a proposed final score.
- Terraform formatting, plus local `terraform validate` **only when provider plugins are already installed locally**. It does not install providers or initialize a backend.
- Shell syntax with `bash -n` and JSON syntax as diagnostics, with no extra rubric deduction.

AST/HCL pattern checks are evidence for review, not a runtime proof. Rows involving effective IAM, document quality, diagram accuracy, missing source patterns, or unavailable historical AWS results stay provisional until reviewed. The [plan](plan.md) and [instruction cross-check](rubric_discrepancies.md) define handout-first scoring decisions.
