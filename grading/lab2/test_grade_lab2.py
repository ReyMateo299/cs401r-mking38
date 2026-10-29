"""Synthetic fixtures only; no student submission is graded by this test file."""

from pathlib import Path

import grade_lab2 as grader
import pytest


def full_review(teardown: str = "present", secret: bool = False) -> dict:
    return {
        "scores": {code: {"score": maximum} for code, _, maximum in grader.RUBRIC},
        "teardown_evidence": teardown,
        "confirmed_secret": secret,
    }


def test_hcl_scanner_ignores_comments_and_balances_nested_blocks():
    files = {
        "infrastructure/modules/vpc/main.tf": '''
# resource "aws_nat_gateway" "fake" {}
resource "aws_nat_gateway" "real" {
  count = var.enable_nat_gateway ? 1 : 0
  tags = { Name = "${var.project}-nat" }
  subnet_id = aws_subnet.public.id
}
'''
    }
    blocks = grader.hcl_blocks(files)
    assert len(grader.resources(blocks, "aws_nat_gateway")) == 1
    assert grader.resources(blocks, "aws_nat_gateway")[0].label == "real"


def test_safe_read_decodes_utf16_apply_log(tmp_path: Path):
    log = tmp_path / "lab2-extend-output.txt"
    log.write_bytes("Apply complete! Resources: 31 added.\n".encode("utf-16"))
    assert "Apply complete!" in grader.safe_read(log)


def test_ast_does_not_count_starter_docstring_as_implementation():
    source = 'def deduplicate(df):\n    """partitionBy transaction_id orderBy"""\n    pass\n'
    body = grader.non_doc_function(source, "deduplicate")
    assert "transaction_id" not in body
    assert "pass" in body


def test_nested_lifecycle_and_feature_definitions_parse():
    files = {
        "infrastructure/modules/storage/main.tf": '''
resource "aws_s3_bucket_lifecycle_configuration" "this" {
  rule {
    id = "expire-raw-data"
    filter { prefix = "raw/" }
    expiration { days = 90 }
  }
}
''',
        "infrastructure/modules/feature_store/main.tf": '''
resource "aws_sagemaker_feature_group" "this" {
  feature_definition {
    feature_type = "Fractional"
    feature_name = "event_time"
  }
}
''',
    }
    blocks = grader.hcl_blocks(files)
    lifecycle = grader.resources(blocks, "aws_s3_bucket_lifecycle_configuration")[0]
    feature_group = grader.resources(blocks, "aws_sagemaker_feature_group")[0]
    assert "expire-raw-data" in grader.child_bodies(lifecycle.body, "rule")[0]
    definition = grader.child_bodies(feature_group.body, "feature_definition")[0]
    assert grader.assignment(definition, "feature_name") == '"event_time"'
    assert grader.assignment(definition, "feature_type") == '"Fractional"'


def test_handout_teardown_cap_and_canvas_comment(tmp_path: Path):
    root = tmp_path / "Synthetic_Student"
    root.mkdir()
    review = full_review("missing")
    review["scores"]["T2.2"] = {"score": 10, "reason": "Only one input date format is parsed."}
    report = grader.grade(root, "Cameron_Example", review)
    assert "Status: **Final**" in report
    assert "Score: **85.5/100**" in report
    assert "Great work Cameron" in report
    assert "T2.2: Only one input date format is parsed. (-2 points)" in report
    assert "Task 1 is capped at 12.5/25 (-12.5 points)" in report
    assert "**T2.2 — Transform functions (-2):**" in report
    assert "**T1.1 —" not in report


def test_confirmed_secret_overrides_all_points(tmp_path: Path):
    root = tmp_path / "Synthetic_Student"
    root.mkdir()
    report = grader.grade(root, "Synthetic_Student", {"confirmed_secret": True})
    assert "Status: **Final**" in report
    assert "Score: **0/100**" in report
    assert "confirmed committed secret" in report


def test_secret_detection_redacts_value():
    secret = "AKIA" + "A" * 16
    candidates = grader.secret_candidates({"code.py": f'key = "{secret}"'})
    assert candidates
    assert secret not in "\n".join(candidates)


def test_static_scan_never_imports_submitted_python(tmp_path: Path):
    root = tmp_path / "Synthetic_Student"
    script = root / "glue-scripts" / "transform.py"
    script.parent.mkdir(parents=True)
    marker = tmp_path / "executed"
    script.write_text(f'open({str(marker)!r}, "w").write("bad")\n', encoding="utf-8")
    report = grader.grade(root, "Synthetic_Student")
    assert "Provisional" in report
    assert not marker.exists()


def test_schema_driven_date_cast_recognizes_both_formats():
    files = {"glue-scripts/transform.py": '''
SCHEMA = {"purchase_date": "date", "customer_id": "string"}
DATE_FORMATS = ["yyyy-MM-dd", "MM/dd/yyyy"]
def cast_types(df):
    for name, target in SCHEMA.items():
        if target == "date":
            df = df.withColumn(name, coalesce(*[to_date(col(name), fmt) for fmt in DATE_FORMATS]))
    return df.filter(col("customer_id").isNotNull())
'''}
    rows = {code: grader.Row(code, title, float(maximum)) for code, title, maximum in grader.RUBRIC}
    grader.task2(rows, [], files)
    assert "Both purchase-date formats not established" not in rows["T2.2"].reasons


def test_review_summary_appears_in_canvas_comment(tmp_path: Path):
    root = tmp_path / "Synthetic_Student"
    root.mkdir()
    review = full_review()
    review["canvas_summary"] = "The contract and lineage diagram satisfy the written criteria."
    report = grader.grade(root, "Synthetic_Student", review)
    assert "The contract and lineage diagram satisfy the written criteria." in report
    assert "No rubric deductions." in report
    assert "Task 1 — Infrastructure and security: **25/25**" in report
    assert "**T1.1 —" not in report


def test_full_credit_written_work_keeps_reason_and_evidence(tmp_path: Path):
    root = tmp_path / "Synthetic_Student"
    root.mkdir()
    review = full_review()
    review["scores"]["T4.1"] = {
        "score": 8,
        "reason": "Nine typed columns and measurable quality guarantees are documented.",
        "evidence": ["docs/lab2-data-contract.md:47"],
    }
    report = grader.grade(root, "Synthetic_Student", review)
    assert "**T4.1 — Data contract: 8/8.** Nine typed columns" in report
    assert "Evidence: docs/lab2-data-contract.md:47" in report
    assert "**T4.1 — Data contract (-" not in report


def test_review_template_requires_reasoned_scores():
    rows = {code: grader.Row(code, title, float(maximum)) for code, title, maximum in grader.RUBRIC}
    rows["T4.1"].candidate = 4
    rows["T4.1"].review = True
    rows["T4.1"].reasons = ["Contract quality needs inspection"]
    template = grader.review_template("Synthetic_Student", rows)
    assert len(template["scores"]) == len(grader.RUBRIC)
    assert template["scores"]["T4.1"]["score"] is None
    assert template["scores"]["T4.1"]["static"]["candidate"] == 4
    assert template["scores"]["T4.1"]["static"]["needs_review"] is True

    template.update(reviewer="Codex", canvas_summary="Reviewed all criteria.", confirmed_secret=False)
    for entry in template["scores"].values():
        entry.update(score=0, reason="No supporting submission evidence.", evidence=["README.md"])
    assert grader.validate_llm_review(template, "Synthetic_Student", rows)

    del template["scores"]["T4.1"]
    with pytest.raises(ValueError, match="coverage mismatch"):
        grader.validate_llm_review(template, "Synthetic_Student", rows)


def test_llm_review_rejects_wrong_student_and_unreasoned_full_credit():
    rows = {code: grader.Row(code, title, float(maximum)) for code, title, maximum in grader.RUBRIC}
    review = grader.review_template("Student_A", rows)
    review.update(reviewer="Codex", canvas_summary="Reviewed all criteria.", confirmed_secret=False)
    for code, _, maximum in grader.RUBRIC:
        review["scores"][code].update(score=maximum, reason="", evidence=["README.md"])
    with pytest.raises(ValueError, match="student_id"):
        grader.validate_llm_review(review, "Student_B", rows)
    with pytest.raises(ValueError, match="including for full credit"):
        grader.validate_llm_review(review, "Student_A", rows)


def test_module_wiring_and_variable_defaults_count_for_static_checks():
    files = {
        "infrastructure/modules/sagemaker/main.tf": '''
resource "aws_sagemaker_domain" "this" {
  app_network_access_type = var.app_network_access_type
  subnet_ids = var.subnet_ids
}
''',
        "infrastructure/environments/dev/main.tf": '''
module "sagemaker" {
  source = "../../modules/sagemaker"
  app_network_access_type = "VpcOnly"
  subnet_ids = [module.vpc.private_subnet_id]
}
''',
        "infrastructure/modules/storage/main.tf": '''
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  rule { id = "expire-raw-data" filter { prefix = "raw/" } expiration { days = var.raw_expiration_days } }
  rule { id = "expire-raw-versions" filter { prefix = "raw/" } noncurrent_version_expiration { noncurrent_days = 30 } }
  rule { id = "expire-processed-versions" filter { prefix = "processed/" } noncurrent_version_expiration { noncurrent_days = 30 } }
  rule { id = "expire-feature-versions" filter { prefix = "features/" } noncurrent_version_expiration { noncurrent_days = 60 } }
  rule { id = "expire-datacapture" filter { prefix = "datacapture/" } expiration { days = var.datacapture_expiration_days } }
}
''',
        "infrastructure/modules/storage/variables.tf": '''
variable "raw_expiration_days" { default = 90 }
variable "datacapture_expiration_days" { default = 7 }
''',
    }
    rows = {code: grader.Row(code, title, float(maximum)) for code, title, maximum in grader.RUBRIC}
    grader.task1(rows, grader.hcl_blocks(files), files)
    assert "SageMaker Domain VpcOnly setting not found" not in rows["T1.1"].reasons
    assert "Lifecycle prefixes or retention periods not established" not in rows["T1.3"].reasons


def test_alternate_post_tag_teardown_evidence_name(tmp_path: Path):
    files = {
        "docs/lab2-destroy-output.txt": "Destroy complete! Resources: 0 destroyed.\nState bucket retained.\n",
        "docs/lab2-teardown-verify-output.txt": (
            "NAT gateways           OK\n"
            "SageMaker domains      OK\n"
            "EFS filesystems        OK\n"
            "No billable Lab 2 resources remain.\n"
        ),
    }
    status, evidence = grader.teardown(tmp_path, files)
    assert status == "present"
    assert "lab2-teardown-verify-output.txt" in evidence


def test_destroy_complete_log_needs_no_later_billable_message(tmp_path: Path):
    files = {
        "docs/lab2-destroy-output.txt": (
            "Terraform destroyed the resources.\n"
            "\x1b[0mDestroy complete! Resources: 34 destroyed.\x1b[0m\n"
        ),
    }
    status, evidence = grader.teardown(tmp_path, files)
    assert status == "present"
    assert "completion" in evidence


def test_legacy_verifier_fail_line_blocks_final_score(tmp_path: Path):
    root = tmp_path / "Synthetic_Student"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "lab2-verify-output.txt").write_text(
        "  FAIL  processed: duplicate transaction_id\nSummary: 35 passed, 0 failed\n",
        encoding="utf-8",
    )
    review = full_review()
    report = grader.grade(root, "Synthetic_Student", review)
    assert "Status: **Provisional" in report
    assert "committed verification FAIL lines" in report
    assert "docs/lab2-verify-output.txt:1" in report

    review["verification_fail_reviewed"] = True
    review["verification_fail_reason"] = "Reviewed the duplicate transaction finding and adjusted T2.2."
    review["scores"]["T2.2"] = {"score": 9, "reason": "Duplicate transaction IDs remain."}
    report = grader.grade(root, "Synthetic_Student", review)
    assert "Status: **Final**" in report
    assert "Score: **97/100**" in report


def test_only_roster_or_approved_external_checkout_is_accepted(tmp_path: Path, monkeypatch):
    instructor_child = tmp_path / "instructor" / "grading" / "lab2" / "Student_One"
    instructor_child.mkdir(parents=True)
    external = tmp_path / "cs401r-jsims1"
    external.mkdir()
    monkeypatch.setattr(grader, "SUBMISSIONS", instructor_child.parent)
    monkeypatch.setattr(grader, "EXTERNAL_SUBMISSIONS", {external: "Jared_Cook_Sims"})
    assert grader.submission_student_id(instructor_child) == "Student_One"
    assert grader.submission_student_id(external) == "Jared_Cook_Sims"
    with pytest.raises(ValueError, match="approved external checkout"):
        grader.submission_student_id(tmp_path)
