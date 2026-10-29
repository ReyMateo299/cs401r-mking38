#!/usr/bin/env python3
"""Offline, single-submission Lab 2 grader. Never executes submitted code or AWS CLI."""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable


HERE = Path(__file__).resolve().parent
SUBMISSIONS = (HERE.parents[2] / "cs401r-2026-instructor" / "grading" / "lab2").resolve()
EXTERNAL_SUBMISSIONS = {
    (HERE.parents[2] / "cs401r-jsims1").resolve(): "Jared_Cook_Sims",
}
MAX_FILE = 2_000_000
SKIP_DIRS = {".git", ".terraform", "__pycache__", ".venv", "venv", "node_modules"}
RUBRIC = [
    ("T1.1", "Private subnet, NAT, Domain", 10),
    ("T1.2", "IAM roles and boundaries", 8),
    ("T1.3", "S3 lifecycle rules", 4),
    ("T1.4", "LocalStack validation", 3),
    ("T2.1", "Catalog and crawler table", 6),
    ("T2.2", "Transform functions", 12),
    ("T2.3", "Glue module apply", 4),
    ("T2.4", "Transform job succeeded", 3),
    ("T3.1", "Feature functions", 10),
    ("T3.2", "Temporal split", 4),
    ("T3.3", "Feature Group", 3),
    ("T3.4", "Feature job succeeded", 3),
    ("T4.1", "Data contract", 8),
    ("T4.2", "Lineage diagram", 7),
    ("T5.1", "Module organization", 4),
    ("T5.2", "Parameterization", 3),
    ("T5.3", "Terraform fmt and validate", 3),
    ("T5.4", "Extend apply evidence", 3),
    ("T5.5", "README", 2),
]
assert sum(row[2] for row in RUBRIC) == 100
TASKS = [
    (1, "Infrastructure and security", 25, "Private networking, IAM, lifecycle, and LocalStack evidence met the requirements."),
    (2, "Data catalog and ETL", 25, "Catalog, transform logic, and job evidence met the requirements."),
    (3, "Features and Feature Store", 20, "Temporal features, Feature Group, and job evidence met the requirements."),
    (4, "Written artifacts", 15, "Data contract and lineage diagram met the requirements; details below."),
    (5, "Repository quality", 15, "Terraform organization, validation, apply evidence, and README met the requirements."),
]
WRITTEN_CODES = {"T4.1", "T4.2", "T5.5"}
FEATURES = {
    "customer_id": "String", "event_time": "Fractional",
    "days_since_last_purchase": "Fractional", "customer_tenure_days": "Fractional",
    "purchase_frequency_30d": "Fractional", "purchase_frequency_90d": "Fractional",
    "purchase_frequency_180d": "Fractional", "avg_order_value": "Fractional",
    "total_spend_90d": "Fractional", "total_lifetime_value": "Fractional",
    "avg_basket_size_6m": "Fractional", "category_diversity_score": "Fractional",
    "online_to_store_ratio": "Fractional", "loyalty_tier": "String",
    "churn_risk_score": "Fractional", "churn_label": "Integral",
}


@dataclass
class Block:
    kind: str
    name: str
    label: str
    body: str
    path: str
    line: int


@dataclass
class Row:
    code: str
    title: str
    maximum: float
    candidate: float = 0
    score: float | None = None
    reasons: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    review: bool = False

    def check(self, ok: bool, points: float, reason: str, evidence: str = "") -> None:
        if ok:
            self.candidate += points
            if evidence:
                self.evidence.append(evidence)
        else:
            self.reasons.append(reason)
            self.review = True

    def finish(self) -> None:
        self.candidate = round(min(self.maximum, self.candidate), 2)
        if not self.review:
            self.score = self.candidate


def fmt_points(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.1f}"


def submission_student_id(root: Path) -> str:
    """Accept one roster submission, including the approved external checkout."""
    if not root.is_dir():
        raise ValueError(f"submission directory does not exist: {root}")
    if root.parent == SUBMISSIONS:
        return root.name
    if root in EXTERNAL_SUBMISSIONS:
        return EXTERNAL_SUBMISSIONS[root]
    raise ValueError(f"submission must be one directory under {SUBMISSIONS} or an approved external checkout")


def safe_read(path: Path) -> str:
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_FILE:
            return ""
        content = path.read_bytes()
        if content.startswith((b"\xff\xfe", b"\xfe\xff")):
            return content.decode("utf-16", errors="replace")
        return content.decode("utf-8-sig", errors="replace")
    except OSError:
        return ""


def inventory(root: Path) -> dict[str, str]:
    out = {}
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() in {".tf", ".py", ".sh", ".md", ".txt", ".json", ".hcl", ".tfvars", ".tfstate"} or p.name in {"Makefile", ".env"}:
            if p.is_file():
                out[p.relative_to(root).as_posix()] = safe_read(p)
    return out


def mask_hcl_comments(source: str) -> str:
    """Preserve offsets/newlines, including quoted # and // characters."""
    chars = list(source)
    i, state = 0, "code"
    while i < len(chars):
        c, nxt = chars[i], chars[i + 1] if i + 1 < len(chars) else ""
        if state == "code":
            if c == '"':
                state = "string"
            elif c == "#" or (c == "/" and nxt == "/"):
                state = "line"
            elif c == "/" and nxt == "*":
                state = "block"
                chars[i] = chars[i + 1] = " "
                i += 2
                continue
        elif state == "string":
            if c == "\\":
                i += 2
                continue
            if c == '"':
                state = "code"
        elif state == "line":
            if c == "\n":
                state = "code"
            else:
                chars[i] = " "
        elif state == "block":
            if c == "*" and nxt == "/":
                chars[i] = chars[i + 1] = " "
                i += 2
                state = "code"
                continue
            if c != "\n":
                chars[i] = " "
        i += 1
    return "".join(chars)


BLOCK_START = re.compile(r'\b(resource|module|variable|output)\s+"([^"\n]+)"(?:\s+"([^"\n]+)")?\s*\{')


def closing_brace(source: str, opening: int) -> int:
    depth, quoted, escaped = 0, False, False
    for i in range(opening, len(source)):
        c = source[i]
        if quoted:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quoted = False
            continue
        if c == '"':
            quoted = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def child_bodies(source: str, name: str) -> list[str]:
    out = []
    for match in re.finditer(rf"\b{re.escape(name)}\s*\{{", source):
        end = closing_brace(source, match.end() - 1)
        if end >= 0:
            out.append(source[match.end():end])
    return out


def hcl_blocks(files: dict[str, str]) -> list[Block]:
    found = []
    for path, raw in files.items():
        if not path.endswith(".tf"):
            continue
        src = mask_hcl_comments(raw)
        for match in BLOCK_START.finditer(src):
            end = closing_brace(src, match.end() - 1)
            if end < 0:
                continue
            found.append(Block(match[1], match[2], match[3] or "", src[match.end():end],
                               path, src.count("\n", 0, match.start()) + 1))
    return found


def resources(blocks: Iterable[Block], type_name: str, path_part: str = "") -> list[Block]:
    return [b for b in blocks if b.kind == "resource" and b.name == type_name
            and path_part in b.path]


def modules(blocks: Iterable[Block], name: str = "") -> list[Block]:
    return [b for b in blocks if b.kind == "module" and (not name or b.name == name)]


def assignment(body: str, key: str) -> str:
    match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*([^\n]+)", body)
    return match[1].strip() if match else ""


def contains_any(text: str, *parts: str) -> bool:
    return any(p.lower() in text.lower() for p in parts)


def loc(block: Block | None) -> str:
    return f"{block.path}:{block.line}" if block else ""


def first(blocks: list[Block]) -> Block | None:
    return blocks[0] if blocks else None


def blob(files: dict[str, str], fragment: str) -> str:
    return "\n".join(v for k, v in files.items() if fragment in k)


def find_path(files: dict[str, str], *options: str) -> str:
    for option in options:
        if option in files:
            return option
    return ""


def non_doc_function(source: str, name: str) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                body = body[1:]
            return "\n".join(ast.unparse(item) for item in body)
    return ""


def line_of(files: dict[str, str], path: str, needle: str) -> str:
    if not path:
        return ""
    for number, line in enumerate(files.get(path, "").splitlines(), 1):
        if needle.lower() in line.lower():
            return f"{path}:{number}"
    return path


def tf_value(blocks: list[Block], name: str, default: str) -> bool:
    return any(b.kind == "variable" and b.name == name and default in assignment(b.body, "default") for b in blocks)


def task1(rows: dict[str, Row], blocks: list[Block], files: dict[str, str]) -> None:
    r = rows["T1.1"]
    private = first([b for b in resources(blocks, "aws_subnet") if contains_any(b.body, "private_subnet_cidr", "10.0.1.0/24")])
    nat = first(resources(blocks, "aws_nat_gateway"))
    eip = first(resources(blocks, "aws_eip"))
    domain = first(resources(blocks, "aws_sagemaker_domain"))
    tf_source = "\n".join(v for k, v in files.items() if k.endswith(".tf"))
    route = any("nat_gateway_id" in b.body and "0.0.0.0/0" in b.body for b in resources(blocks, "aws_route") + resources(blocks, "aws_route_table"))
    assoc = any("private" in b.body.lower() or "private" in b.label.lower() for b in resources(blocks, "aws_route_table_association"))
    self_ingress = any("self" in b.body and "true" in b.body and '"-1"' in b.body
                       for b in resources(blocks, "aws_security_group") + resources(blocks, "aws_security_group_rule") + resources(blocks, "aws_vpc_security_group_ingress_rule"))
    r.check(bool(private), 1, "Private subnet definition not found", loc(private))
    r.check(bool(private and "10.0.1.0/24" in tf_source and "us-east-1a" in tf_source), 0.5,
            "Private subnet CIDR/AZ not established", loc(private))
    r.check(bool(private and ("false" in assignment(private.body, "map_public_ip_on_launch") or not assignment(private.body, "map_public_ip_on_launch"))), 0.5, "Private subnet may assign public IPs", loc(private))
    r.check(bool(nat and eip and "allocation_id" in nat.body and "public" in assignment(nat.body, "subnet_id").lower()), 2,
            "Public-subnet NAT with EIP association not established", loc(nat))
    r.check(route and assoc, 1, "Private route to NAT and subnet association not established", loc(first(resources(blocks, "aws_route"))))
    r.check(self_ingress, 0.5, "Self-referencing all-protocol security-group ingress not established", loc(first(resources(blocks, "aws_security_group"))))
    guard = tf_value(blocks, "enable_nat_gateway", "true") and bool(nat and contains_any(nat.body, "enable_nat_gateway"))
    output = any(b.kind == "output" and b.name == "private_subnet_id" for b in blocks)
    r.check(guard and output, 1, "NAT guard/default or private-subnet output not found", loc(nat))
    domain_subnets = assignment(domain.body, "subnet_ids") if domain else ""
    sage_wiring = "\n".join(b.body for b in modules(blocks, "sagemaker"))
    private_wired = "private" in domain_subnets.lower() or ("subnet_ids" in domain_subnets and "private_subnet_id" in sage_wiring)
    r.check(bool(domain and private_wired), 2,
            "SageMaker Domain private-subnet reference not found", loc(domain))
    network_value = assignment(domain.body, "app_network_access_type") if domain else ""
    network_ok = "VpcOnly" in network_value or (
        network_value.startswith("var.") and
        any(b.kind == "variable" and b.name == network_value[4:] and "VpcOnly" in assignment(b.body, "default")
            for b in blocks))
    if not network_ok and network_value.startswith("var."):
        wired = "\n".join(b.body for b in modules(blocks, "sagemaker"))
        assigned = assignment(wired, "app_network_access_type")
        network_ok = "VpcOnly" in assigned or (
            assigned.startswith("var.") and any(
                b.kind == "variable" and b.name == assigned[4:] and "VpcOnly" in assignment(b.body, "default")
                for b in blocks))
    r.check(bool(domain and network_ok), 1.5,
            "SageMaker Domain VpcOnly setting not found", loc(domain))
    r.finish()

    r = rows["T1.2"]
    iam = blob(files, "modules/iam/")
    iam_code = mask_hcl_comments(iam)
    roles = resources(blocks, "aws_iam_role", "modules/iam/")
    role_text = "\n".join(b.body for b in roles)
    r.check(all(name in role_text for name in ("MLEngineer", "DataEngineer", "ModelMonitor")), 2,
            "Three role definitions not established", loc(first(roles)))
    r.check(all(service in iam_code for service in ("glue.amazonaws.com", "lambda.amazonaws.com", "sagemaker.amazonaws.com")), 2,
            "Required DataEngineer and ModelMonitor trust principals not established", loc(first(roles)))
    r.check(all(prefix in iam_code for prefix in ("raw/", "processed/", "features/", "artifacts/glue/")), 2,
            "DataEngineer S3 prefix access not established", loc(first(roles)))
    r.check("artifacts/" in iam_code and "cloudwatch" in iam_code.lower(), 1,
            "ModelMonitor read and CloudWatch policy not established", loc(first(roles)))
    r.check("s3:PutObject" in iam_code and "s3:GetObject" in iam_code, 1,
            "IAM read/write policy actions not established; review least privilege", loc(first(roles)))
    # Effective policy scope cannot be proven by string matches.
    r.review = True
    r.reasons.append("Review effective IAM scope and trust per role; string matches are only structural signals")
    r.finish()

    r = rows["T1.3"]
    life = first(resources(blocks, "aws_s3_bucket_lifecycle_configuration"))
    text = life.body if life else ""
    rule_ids = ["expire-raw-data", "expire-raw-versions", "expire-processed-versions", "expire-feature-versions", "expire-datacapture"]
    rules = child_bodies(text, "rule")
    rule_map = {re.search(r'(?m)^\s*id\s*=\s*"([^"\n]+)"', body)[1]: body
                for body in rules if re.search(r'(?m)^\s*id\s*=\s*"([^"\n]+)"', body)}
    storage_source = mask_hcl_comments(blob(files, "modules/storage/"))
    if "local.lifecycle_rules" in text:
        for name in rule_ids:
            match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{([^}}]+)\}}", storage_source)
            if match:
                rule_map[name] = match[1]
    found = sum(name in rule_map for name in rule_ids)
    r.check(bool(life), 1, "S3 lifecycle configuration not found", loc(life))
    r.check(found == 5, 2, f"Found {found}/5 named lifecycle rules", loc(life))
    expected = {
        "expire-raw-data": ("raw/", "days", "90"),
        "expire-raw-versions": ("raw/", "noncurrent_days", "30"),
        "expire-processed-versions": ("processed/", "noncurrent_days", "30"),
        "expire-feature-versions": ("features/", "noncurrent_days", "60"),
        "expire-datacapture": ("datacapture/", "days", "7"),
    }
    def retention_matches(rule: str, key: str, expected_days: str) -> bool:
        match = re.search(rf"\b{key}\s*=\s*(\d+|var\.[A-Za-z_][A-Za-z0-9_]*)", rule)
        if not match:
            return False
        value = match[1]
        if value == expected_days:
            return True
        return value.startswith("var.") and any(
            b.kind == "variable" and "/modules/storage/" in "/" + b.path and
            b.name == value[4:] and assignment(b.body, "default") == expected_days
            for b in blocks
        )

    details_ok = all(prefix in rule_map.get(name, "") and
                     retention_matches(rule_map.get(name, ""), day_key, days)
                     for name, (prefix, day_key, days) in expected.items())
    r.check(details_ok, 1,
            "Lifecycle prefixes or retention periods not established", loc(life))
    r.finish()

    r = rows["T1.4"]
    path = find_path(files, "docs/lab2-localstack-output.txt")
    log = files.get(path, "")
    local = blob(files, "environments/local/")
    r.check(bool(path), 1, "LocalStack output not submitted", path)
    r.check(bool(log and all(x in log for x in ("MLEngineer", "DataEngineer", "ModelMonitor"))), 1,
            "Three IAM roles not evidenced in LocalStack output", path)
    nat_absent = bool(re.search(r"(?i)(?:no|none|zero|0|skip(?:ped)?|disabled).{0,35}nat|nat.{0,35}(?:none|zero|0|skip(?:ped)?|disabled)", log))
    r.check("enable_nat_gateway" in local and "false" in local and "vpc" in log.lower() and nat_absent, 1,
            "LocalStack VPC and NAT guard/absence not established", path)
    if re.search(r"(?m)^\s*FAIL\b|\bError:", log):
        r.review = True
        r.reasons.append("LocalStack log contains FAIL/Error markers")
    r.finish()


def task2(rows: dict[str, Row], blocks: list[Block], files: dict[str, str]) -> None:
    r = rows["T2.1"]
    db = first(resources(blocks, "aws_glue_catalog_database"))
    crawler = first(resources(blocks, "aws_glue_crawler"))
    verify = files.get("docs/lab2-verify-output.txt", "")
    r.check(bool(db and contains_any(db.body, "northstar_dev", "project", "environment")), 2,
            "Glue Catalog database definition not found", loc(db))
    glue_source = mask_hcl_comments(blob(files, "modules/glue/"))
    raw_target = bool(crawler and ("raw/customers/" in crawler.body or
                  ("local.raw_path" in crawler.body and "raw/${var.dataset}/" in glue_source and
                   re.search(r'(?s)variable\s+"dataset"\s*\{[^}]*default\s*=\s*"customers"', glue_source))))
    r.check(bool(raw_target and crawler and contains_any(crawler.body, "data_engineer", "DataEngineer")), 2,
            "Crawler raw/customers target or DataEngineer role not established", loc(crawler))
    table_pass = bool(re.search(r"(?im)^\s*PASS\s+.*crawler registered a table", verify))
    table_fail = bool(re.search(r"(?im)^\s*FAIL\s+.*crawler registered a table", verify))
    # Some students were assigned an earlier rubric that asked for
    # `aws glue get-table ...` to return a schema but did not require saving
    # the command output. In that grading context, absence of the verifier
    # file alone cannot cost the table points; configuration is the available
    # offline evidence unless a saved FAIL contradicts it.
    table_evidence = table_pass or (not table_fail and bool(db and crawler and raw_target))
    r.check(table_evidence, 2,
            "No crawler table result is saved; under the earlier rubric, a saved output file was not required",
            "docs/lab2-verify-output.txt")
    r.finish()

    r = rows["T2.2"]
    path = find_path(files, "glue-scripts/transform.py", "data/glue-scripts/transform.py")
    source = files.get(path, "")
    cast = non_doc_function(source, "cast_types")
    impute = non_doc_function(source, "impute_nulls")
    dedup = non_doc_function(source, "deduplicate")
    r.check(bool(cast), 0.5, "cast_types implementation not found", line_of(files, path, "def cast_types"))
    r.check(bool(cast and contains_any(cast, "cast(", "astype(", "SCHEMA")), 1,
            "Schema type casting not established", line_of(files, path, "def cast_types"))
    r.check(bool(cast and "customer_id" in cast and contains_any(cast, "isNotNull", "dropna", "filter")), 1,
            "Null customer_id removal not established", line_of(files, path, "def cast_types"))
    date_source = cast
    if "DATE_FORMATS" in cast:
        date_source += "\n" + "\n".join(line for line in source.splitlines() if re.match(r"^DATE_FORMATS\s*=", line))
    date_target = "purchase_date" in cast or bool(
        "SCHEMA" in cast and re.search(r'["\']purchase_date["\']\s*:\s*["\']date["\']', source)
    )
    r.check(bool(cast and date_target and contains_any(date_source, "MM/dd/yyyy", "%m/%d/%Y") and contains_any(date_source, "yyyy-MM-dd", "%Y-%m-%d")), 1.5,
            "Both purchase-date formats not established", line_of(files, path, "def cast_types"))
    r.check(bool(impute and contains_any(impute, "0.5", "median", "percentile")), 2,
            "Median numeric imputation not established", line_of(files, path, "def impute_nulls"))
    r.check(bool(impute and "unknown" in impute), 2,
            "String imputation to 'unknown' not established", line_of(files, path, "def impute_nulls"))
    r.check(bool(dedup and "transaction_id" in dedup and contains_any(dedup, "partitionBy", "dropDuplicates", "duplicated", "groupBy")), 3,
            "Transaction-ID deduplication not established", line_of(files, path, "def deduplicate"))
    r.check(bool(dedup and contains_any(dedup, "orderBy", "sort_values", "sortWithinPartitions")), 1,
            "Deterministic duplicate tie-break not established", line_of(files, path, "def deduplicate"))
    if dedup and "customer_id" in dedup and "partitionBy('customer_id')" in dedup.replace('"', "'"):
        r.review = True
        r.reasons.append("Possible customer-level deduplication; inspect grain")
    main = non_doc_function(source, "main")
    if main and not all(f"{name}(" in main for name in ("cast_types", "impute_nulls", "deduplicate")):
        r.review = True
        r.reasons.append("Transform entry point may not invoke all three functions")
    r.finish()

    r = rows["T2.3"]
    glue = [b for b in blocks if "/modules/glue/" in "/" + b.path]
    types = {b.name for b in glue if b.kind == "resource"}
    apply = files.get("docs/lab2-extend-output.txt", "")
    r.check(bool(glue), 1, "Glue module not found", loc(first(glue)))
    r.check({"aws_glue_crawler", "aws_glue_job"}.issubset(types), 1,
            "Glue database/crawler/job definitions incomplete", loc(first(glue)))
    last_apply = apply.rsplit("Apply complete!", 1)[-1] if "Apply complete!" in apply else apply
    clean_apply = "Apply complete!" in apply and not re.search(r"(?m)^Error:", last_apply)
    r.check(clean_apply, 2,
            "Committed apply log does not show a clean apply", "docs/lab2-extend-output.txt")
    r.finish()

    job_row(rows["T2.4"], files, "transform", blocks, legacy_missing_output_ok=True)


def job_row(row: Row, files: dict[str, str], job: str, blocks: list[Block],
            legacy_missing_output_ok: bool = False) -> None:
    path = "docs/lab2-verify-output.txt"
    log = files.get(path, "")
    pattern = rf"(?im)^\s*(PASS|FAIL)\s+job\s+[^\n]*{re.escape(job)}[^\n]*?(SUCCEEDED|FAILED|last run: [^\n]*)?\s*$"
    matches = list(re.finditer(pattern, log))
    passed = bool(matches and matches[-1][1].upper() == "PASS" and "SUCCEEDED" in matches[-1][0].upper())
    # Shipped verifier's PASS line omits the word SUCCEEDED in some revisions.
    if matches and matches[-1][1].upper() == "PASS":
        passed = True
    if not matches and legacy_missing_output_ok:
        apply = files.get("docs/lab2-extend-output.txt", "")
        last_apply = apply.rsplit("Apply complete!", 1)[-1] if "Apply complete!" in apply else apply
        configured = any(b.kind == "resource" and b.name == "aws_glue_job" and
                         job in (b.label + " " + b.body + " " + b.path).lower() for b in blocks)
        # The earlier rubric required a successful get-job-run result but did
        # not require a committed verifier file. Don't convert an absent saved
        # result into failure; use a configured job and clean apply as the
        # available offline evidence, while keeping the runtime result explicit.
        passed = configured and "Apply complete!" in apply and not re.search(r"(?m)^Error:", last_apply)
        reason = (f"No saved {job} job-run result is available; the legacy rubric did not require a saved output file"
                  if passed else f"{job} job success is not established by job configuration and apply evidence")
    elif matches:
        reason = f"Latest saved verifier result for {job} job is not PASS"
    else:
        reason = f"Latest committed verifier result for {job} job is not PASS"
    row.check(passed, 3, reason, path)
    row.finish()


def task3(rows: dict[str, Row], blocks: list[Block], files: dict[str, str]) -> None:
    path = find_path(files, "glue-scripts/feature_engineer.py", "data/glue-scripts/feature_engineer.py")
    source = files.get(path, "")
    fn = {name: non_doc_function(source, name) for name in (
        "split_windows", "compute_rfm_features", "assign_loyalty_tier",
        "compute_churn_proxy", "attach_churn_label")}
    r = rows["T3.1"]
    split = fn["split_windows"]
    r.check(bool(split and "FEATURE_CUTOFF" in split and "SNAPSHOT" in split), 2,
            "Observation/outcome window implementation not established", line_of(files, path, "def split_windows"))
    rfm = fn["compute_rfm_features"]
    r.check(bool(rfm and "groupBy" in rfm and "customer_id" in rfm), 1,
            "Customer-level RFM aggregation not established", line_of(files, path, "def compute_rfm_features"))
    rfm_columns = ("days_since_last_purchase", "customer_tenure_days", "purchase_frequency_30d",
                   "purchase_frequency_90d", "purchase_frequency_180d", "avg_order_value",
                   "total_spend_90d", "total_lifetime_value", "avg_basket_size_6m",
                   "category_diversity_score", "online_to_store_ratio")
    r.check(bool(rfm and all(x in rfm for x in rfm_columns)), 2,
            "Eleven RFM feature columns not established", line_of(files, path, "def compute_rfm_features"))
    tier = fn["assign_loyalty_tier"]
    tier_constants = "\n".join(line for line in source.splitlines() if re.match(r"^TIER_[A-Z_]+\s*=", line))
    tier_source = tier_constants + tier
    r.check(bool(tier and all(str(n) in tier_source for n in (500, 2000, 5000)) and all(x in tier for x in ("Bronze", "Silver", "Gold", "Platinum"))), 2,
            "Four loyalty tiers or thresholds not established", line_of(files, path, "def assign_loyalty_tier"))
    risk = fn["compute_churn_proxy"]
    r.check(bool(risk and "days_since_last_purchase" in risk and "churn_risk_score" in risk
                 and contains_any(risk, "least", "clip", "min(", "greatest")
                 and ("*" in risk or "/" in risk)), 2,
            "Scaled/clamped churn proxy not established", line_of(files, path, "def compute_churn_proxy"))
    label = fn["attach_churn_label"]
    r.check(bool(label and "holdout" in label and "churn_label" in label and contains_any(label, "join", "isin", "merge")), 1,
            "Churn label from outcome window not established", line_of(files, path, "def attach_churn_label"))
    main = non_doc_function(source, "main")
    if main and not all(f"{name}(" in main for name in fn):
        r.review = True
        r.reasons.append("Feature-job entry point may not invoke all five functions")
    r.finish()

    r = rows["T3.2"]
    r.check(bool(split and "FEATURE_CUTOFF" in split and "SNAPSHOT" in split
                 and "purchase_date" in split and "<=" in split and ">" in split), 2,
            "Fixed observation/outcome boundaries not established", line_of(files, path, "def split_windows"))
    rfm = fn["compute_rfm_features"]
    r.check(bool(rfm and "FEATURE_CUTOFF" in rfm and not contains_any(rfm, "current_date(", "today(")), 1,
            "RFM windows may not be anchored to FEATURE_CUTOFF", line_of(files, path, "def compute_rfm_features"))
    r.check(bool(label and "holdout" in label and not contains_any(label, "days_since_last_purchase", "churn_risk_score")), 1,
            "Label may derive from features rather than the outcome window", line_of(files, path, "def attach_churn_label"))
    if contains_any(split + rfm, "current_date(", "today("):
        r.review = True
        r.reasons.append("Dynamic date anchor found; inspect for reproducibility")
    r.finish()

    r = rows["T3.3"]
    group = first(resources(blocks, "aws_sagemaker_feature_group", "modules/feature_store/"))
    definitions = []
    for body in child_bodies(group.body, "feature_definition") if group else []:
        name = assignment(body, "feature_name").strip('"')
        kind = assignment(body, "feature_type").strip('"')
        if name and kind:
            definitions.append((name, kind))
    if group and "var.feature_definitions" in group.body:
        variable = next((b for b in blocks if b.kind == "variable" and b.name == "feature_definitions"
                         and "modules/feature_store/" in b.path), None)
        if variable:
            definitions = re.findall(r'\{\s*name\s*=\s*"([^"\n]+)"\s*,?\s*type\s*=\s*"([^"\n]+)"\s*\}',
                                     variable.body)
    found = dict(definitions)
    r.check(bool(group), 0.5, "Feature Group module resource not found", loc(group))
    r.check(bool(group and len(definitions) == 16 and found == FEATURES), 1.5,
            f"Feature definitions/types incomplete ({len(definitions)}/16 parsed)", loc(group))
    offline_var = any(b.kind == "variable" and b.name == "offline_store_prefix" and
                      "features/offline-store" in assignment(b.body, "default") for b in blocks)
    offline_ok = bool(group and ("features/offline-store/" in group.body or
                      ("offline_store_prefix" in group.body and offline_var)))
    r.check(bool(group and "enable_online_store" in group.body and "true" in assignment(group.body, "enable_online_store") and offline_ok), 1,
            "Online/offline store separation not established", loc(group))
    r.finish()
    job_row(rows["T3.4"], files, "feature-engineer", blocks, legacy_missing_output_ok=True)


def task4(rows: dict[str, Row], files: dict[str, str], root: Path) -> None:
    r = rows["T4.1"]
    path = "docs/lab2-data-contract.md"
    doc = files.get(path, "")
    for label, pattern, points in (
        ("schema", r"(?im)^#+\s*Schema\b", 2),
        ("three measurable quality guarantees", r"(?im)^#+\s*Quality Guarantees\b", 3),
        ("numeric SLA", r"(?im)^#+\s*SLA\b", 2),
        ("versioning policy", r"(?im)^#+\s*Versioning\b", 1),
    ):
        r.check(bool(re.search(pattern, doc)), points, f"Data contract {label} section not found", path)
    r.review = True
    r.reasons.append("TA must assess schema, measurable guarantees, numeric SLA and breaking-change policy")
    r.finish()

    r = rows["T4.2"]
    diagram = root / "docs/lab2-data-lineage.png"
    r.check(diagram.is_file() and not diagram.is_symlink(), 7, "Lineage diagram image not found", "docs/lab2-data-lineage.png")
    r.review = True
    r.reasons.append("TA must inspect flow nodes, formats on edges, and IAM roles on write edges")
    r.finish()


def task5(rows: dict[str, Row], blocks: list[Block], files: dict[str, str], root: Path) -> None:
    r = rows["T5.1"]
    glue = [b for b in blocks if "/modules/glue/" in "/" + b.path and b.kind == "resource"]
    fg = [b for b in blocks if "/modules/feature_store/" in "/" + b.path and b.kind == "resource"]
    r.check(bool(glue), 1, "modules/glue/ resource definitions not found", loc(first(glue)))
    r.check(bool(fg), 1, "modules/feature_store/ resource definitions not found", loc(first(fg)))
    r.check(all(b.name != "aws_sagemaker_feature_group" for b in glue) and all(b.name != "aws_glue_job" for b in fg), 1,
            "Glue and Feature Group resources appear in wrong modules", loc(first(glue)))
    r.check(bool(modules(blocks, "glue") and modules(blocks, "feature_store")), 1,
            "Environment does not reference both modules", loc(first(modules(blocks))))
    r.finish()

    r = rows["T5.2"]
    new = [b for b in blocks if b.kind == "resource" and ("/modules/glue/" in "/" + b.path or "/modules/feature_store/" in "/" + b.path)]
    named = [b for b in new if assignment(b.body, "name") or assignment(b.body, "feature_group_name") or assignment(b.body, "database_name")]
    hardcoded = [b for b in named if re.search(r'^"northstar[-_]', assignment(b.body, "name") or assignment(b.body, "feature_group_name") or assignment(b.body, "database_name"))]
    r.check(bool(named), 1, "Named Glue/Feature Store resources not found", loc(first(new)))
    r.check(bool(named and not hardcoded), 2, "Hardcoded Glue/Feature Store resource name found", loc(first(hardcoded)))
    r.finish()

    r = rows["T5.3"]
    infra = root / "infrastructure"
    if infra.is_dir():
        try:
            proc = subprocess.run(["terraform", "fmt", "-check", "-recursive", str(infra)],
                                  capture_output=True, text=True, timeout=30, check=False)
            clean = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            clean = False
    else:
        clean = False
    r.check(clean, 1.5, "terraform fmt -check did not pass", "infrastructure/")
    # Never initialize providers or contact the cloud. Validate only with local plugins.
    local_valid = False
    dev = infra / "environments" / "dev"
    if (dev / ".terraform" / "providers").is_dir():
        try:
            proc = subprocess.run(["terraform", "-chdir=" + str(dev), "validate", "-no-color"],
                                  capture_output=True, text=True, timeout=30, check=False)
            local_valid = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    evidence = "\n".join(v for k, v in files.items() if "terraform" in k.lower() and "valid" in k.lower())
    evidence += "\n" + files.get("docs/lab2-extend-output.txt", "")
    valid = local_valid or bool(re.search(r"(?i)Success! The configuration is valid", evidence))
    # A completed Terraform apply is also strong evidence that validation passed.
    valid = valid or bool(re.search(r"Apply complete! Resources:", files.get("docs/lab2-extend-output.txt", "")))
    r.check(valid, 1.5, "Offline Terraform validation evidence not found", "submitted validation log")
    r.finish()

    r = rows["T5.4"]
    path = "docs/lab2-extend-output.txt"
    log = files.get(path, "")
    r.check("aws_sagemaker_domain" in log, 1, "Extend apply log does not show SageMaker Domain", path)
    r.check(bool(re.search(r"Apply complete!", log)), 1, "Apply complete marker not found", path)
    after_apply = log.rsplit("Apply complete!", 1)[-1] if "Apply complete!" in log else ""
    trailing_outputs_only = bool(after_apply and "Outputs:" in after_apply and not re.search(r"(?m)^Error:", after_apply))
    r.check(bool(re.search(r"Apply complete![^\n]*\s*$", log.strip())) or trailing_outputs_only, 1,
            "Extend log does not end in a successful apply or its Terraform outputs", path)
    r.finish()

    r = rows["T5.5"]
    path = next((p for p in files if Path(p).name.lower() == "readme.md" and "/" not in p), "")
    doc = files.get(path, "").lower()
    r.check(bool(doc and all(x in doc for x in ("glue", "feature"))), 1,
            "README does not describe Lab 2 modules", path)
    r.check(bool(doc and all(x in doc for x in ("crawler", "transform", "feature"))), 1,
            "README does not explain the end-to-end pipeline sequence", path)
    r.finish()


def git_show(root: Path, revision: str, path: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{path}"],
                                capture_output=True, text=True, timeout=10, check=False)
        return result.stdout[:MAX_FILE] if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def teardown(root: Path, files: dict[str, str], override: str = "auto") -> tuple[str, str]:
    if override in {"present", "missing", "unknown"}:
        return override, "TA review override"
    path = "docs/lab2-destroy-output.txt"
    # The handout says this is committed on main/default branch after the tag.
    log = ""
    for revision in ("main", "master"):
        log = git_show(root, revision, path)
        if log:
            break
    source = f"default branch:{path}" if log else path
    if not log:
        log = files.get(path, "")
    if not log:
        return "unknown", "Destroy log unavailable; check default branch separately"
    extra_paths = ("docs/lab2-teardown-verification.txt", "docs/lab2-teardown-verify-output.txt")
    extra_path, extra = "", ""
    for candidate in extra_paths:
        extra = git_show(root, "main", candidate) or git_show(root, "master", candidate) or files.get(candidate, "")
        if extra:
            extra_path = candidate
            break
    clean_detail = all(re.search(rf"(?im)^\s*{name}\s+OK\s*$", extra)
                       for name in ("NAT gateways", "SageMaker domains", "EFS filesystems"))
    # The final no-billable message was added to the kit during the semester.
    # A committed log ending with Terraform's completion line is sufficient
    # evidence for this grading gate; do not infer current AWS state from it.
    plain_log = re.sub(r"\x1b\[[0-9;]*m", "", log)
    log_lines = [line.strip() for line in plain_log.splitlines() if line.strip()]
    completed_at_end = bool(log_lines and re.fullmatch(
        r"Destroy complete!(?:\s+Resources:\s+\d+\s+destroyed\.)?", log_lines[-1]
    ))
    if completed_at_end:
        return "present", f"{source}; committed destroy log ends in completion"
    if "Destroy complete!" in plain_log and ("No billable Lab 2 resources remain" in plain_log or clean_detail):
        return "present", f"{source}; clean teardown verification in {extra_path}" if clean_detail else source
    return "missing", f"{source} does not establish a completed destroy"


SECRET_PATTERNS = [
    re.compile(r"\bAKIA(?!IOSFODNN7EXAMPLE)[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{30,}"),
]


def secret_candidates(files: dict[str, str]) -> list[str]:
    candidates = []
    for path, content in files.items():
        if Path(path).name in {"terraform.tfvars", ".env"} or path.endswith(".tfstate"):
            candidates.append(f"prohibited file: {path}")
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            candidates.append(f"credential-like content: {path} (value redacted)")
    return sorted(set(candidates))


def history_secret_candidates(root: Path) -> list[str]:
    """Search Git history for candidate paths only; never return credential values."""
    if not (root / ".git").exists():
        return []
    try:
        commits = subprocess.run(["git", "-C", str(root), "rev-list", "--all"],
                                 capture_output=True, text=True, timeout=30, check=False)
        if commits.returncode:
            return []
        refs = commits.stdout.splitlines()
        if not refs:
            return []
        pattern = r"AKIA[0-9A-Z]{16}|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|aws_secret_access_key[[:space:]]*[:=][[:space:]]*['\"]?[A-Za-z0-9/+=]{30,}"
        found = subprocess.run(["git", "-C", str(root), "grep", "-I", "-n", "-o", "-E", pattern, *refs, "--"],
                               capture_output=True, text=True, timeout=60, check=False)
        matches = []
        for line in found.stdout.splitlines():
            if "AKIAIOSFODNN7EXAMPLE" in line:
                continue
            parts = line.split(":", 3)
            if len(parts) >= 3:
                matches.append(f"Git-history credential-like content: {parts[0]}:{parts[1]} (value redacted)")
            if len(matches) >= 20:
                break
        names = subprocess.run(["git", "-C", str(root), "log", "--all", "--name-only", "--format="],
                               capture_output=True, text=True, timeout=15, check=False)
        for name in set(names.stdout.splitlines()):
            if Path(name).name in {"terraform.tfvars", ".env"} or name.endswith(".tfstate"):
                matches.append(f"Git-history prohibited file: {name}")
        return sorted(set(matches))[:30]
    except (OSError, subprocess.TimeoutExpired):
        return []


def diagnostics(root: Path, files: dict[str, str]) -> list[str]:
    """Syntax diagnostics for other submitted languages; no extra rubric penalties."""
    notes = []
    for path, source in files.items():
        if path.endswith(".sh"):
            try:
                result = subprocess.run(["bash", "-n", str(root / path)], capture_output=True,
                                        text=True, timeout=10, check=False)
                if result.returncode:
                    notes.append(f"Shell syntax needs review: {path}")
            except (OSError, subprocess.TimeoutExpired):
                notes.append(f"Shell syntax unavailable: {path}")
        elif path.endswith(".json"):
            try:
                json.loads(source)
            except json.JSONDecodeError:
                notes.append(f"JSON syntax needs review: {path}")
        elif path.endswith(".py"):
            try:
                ast.parse(source)
            except SyntaxError:
                notes.append(f"Python syntax needs review: {path}")
    return notes[:30]


def load_review(path: Path | None) -> dict:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("review JSON must be an object")
    return data


def validate_llm_review(review: dict, student: str, rows: dict[str, Row]) -> bool:
    """Require a complete, student-specific audit before LLM scores become proposed final."""
    review_type = review.get("review_type")
    if review_type is None:
        return False
    if review_type != "llm":
        raise ValueError("review_type must be 'llm' when supplied")
    if review.get("student_id") != student:
        raise ValueError(f"LLM review student_id must be {student}")
    if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
        raise ValueError("LLM review needs a reviewer")
    if type(review.get("confirmed_secret")) is not bool:
        raise ValueError("LLM review needs a confirmed_secret decision")
    if not isinstance(review.get("canvas_summary"), str) or not review["canvas_summary"].strip():
        raise ValueError("LLM review needs a canvas_summary")
    scores = review.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("LLM review needs rubric scores")
    missing = sorted(set(rows) - set(scores))
    extra = sorted(set(scores) - set(rows))
    if missing or extra:
        raise ValueError(f"LLM review rubric coverage mismatch; missing={missing}, extra={extra}")
    for code, entry in scores.items():
        if not isinstance(entry, dict):
            raise ValueError(f"LLM review {code} must be an object")
        if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
            raise ValueError(f"LLM review {code} needs a reason, including for full credit")
        evidence = entry.get("evidence")
        if not isinstance(evidence, list) or not evidence or not all(
            isinstance(item, str) and item.strip() for item in evidence
        ):
            raise ValueError(f"LLM review {code} needs at least one evidence reference")
    return True


def apply_review(rows: dict[str, Row], review: dict) -> None:
    overrides = review.get("scores", {})
    if not isinstance(overrides, dict):
        raise ValueError("review.scores must be an object")
    for code, value in overrides.items():
        if code not in rows or not isinstance(value, dict):
            raise ValueError(f"invalid review row: {code}")
        score = value.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= rows[code].maximum:
            raise ValueError(f"{code} score must be between 0 and {rows[code].maximum}")
        reason = value.get("reason", "")
        if score < rows[code].maximum and (not isinstance(reason, str) or not reason.strip()):
            raise ValueError(f"{code} deductions need a reason")
        rows[code].score = float(score)
        rows[code].review = False
        rows[code].reasons = [reason.strip()] if reason.strip() else []
        reviewed_evidence = value.get("evidence", [])
        if not isinstance(reviewed_evidence, list) or not all(isinstance(item, str) for item in reviewed_evidence):
            raise ValueError(f"{code} evidence must be a list of strings")
        rows[code].evidence = list(dict.fromkeys(reviewed_evidence + rows[code].evidence))


def canvas_summary(review: dict) -> str | None:
    summary = review.get("canvas_summary")
    if summary is None:
        return None
    if not isinstance(summary, str) or not summary.strip():
        raise ValueError("canvas_summary must be a nonempty string")
    return summary.strip()


def verify_log_findings(log: str) -> tuple[list[int], int | None]:
    """Read each FAIL marker; old verifiers can omit them from their total."""
    fail_lines = [number for number, line in enumerate(log.splitlines(), 1)
                  if re.search(r"\bFAIL\b", line)]
    summary = re.search(r"(?im)^\s*Summary:\s*(\d+)\s+passed,\s*\d+\s+failed", log)
    return fail_lines, int(summary[1]) if summary else None


def analyze(root: Path) -> tuple[dict[str, str], dict[str, Row]]:
    """Collect static candidates once for the report and editable review template."""
    files = inventory(root)
    blocks = hcl_blocks(files)
    rows = {code: Row(code, title, float(maximum)) for code, title, maximum in RUBRIC}
    task1(rows, blocks, files)
    task2(rows, blocks, files)
    task3(rows, blocks, files)
    task4(rows, files, root)
    task5(rows, blocks, files, root)
    return files, rows


def review_template(student: str, rows: dict[str, Row]) -> dict:
    """Provide the LLM with static hints without pre-approving any score."""
    return {
        "review_type": "llm",
        "student_id": student,
        "reviewer": "",
        "canvas_summary": "",
        "review_notes": [],
        "verification_fail_reviewed": None,
        "verification_fail_reason": "",
        "teardown_evidence": "auto",
        "confirmed_secret": None,
        "scores": {
            code: {
                "score": None,
                "reason": "",
                "evidence": [],
                "static": {
                    "candidate": row.candidate,
                    "needs_review": row.review,
                    "flags": row.reasons,
                    "evidence": list(dict.fromkeys(row.evidence)),
                },
            }
            for code, row in rows.items()
        },
    }


def grade(root: Path, student: str, review: dict | None = None,
          analysis: tuple[dict[str, str], dict[str, Row]] | None = None) -> str:
    review = review or {}
    files, rows = analysis if analysis is not None else analyze(root)
    llm_review = validate_llm_review(review, student, rows)
    apply_review(rows, review)
    summary = canvas_summary(review)
    candidates = sorted(set(secret_candidates(files) + history_secret_candidates(root)))
    secret_decision = review.get("confirmed_secret")
    if secret_decision is not None and type(secret_decision) is not bool:
        raise ValueError("confirmed_secret must be true or false")
    gate, gate_evidence = teardown(root, files, review.get("teardown_evidence", "auto"))
    fail_lines, verify_passes = verify_log_findings(files.get("docs/lab2-verify-output.txt", ""))
    fail_reviewed = review.get("verification_fail_reviewed")
    if fail_reviewed is not None and type(fail_reviewed) is not bool:
        raise ValueError("verification_fail_reviewed must be true or false")
    fail_reason = review.get("verification_fail_reason", "")
    if fail_lines and fail_reviewed is True and (not isinstance(fail_reason, str) or not fail_reason.strip()):
        raise ValueError("reviewed verification FAIL lines need a verification_fail_reason")
    security_pending = secret_decision is None
    pending = [r.code for r in rows.values() if r.score is None]
    if gate == "unknown":
        pending.append("teardown gate")
    if security_pending:
        pending.append("security review")
    if fail_lines and fail_reviewed is not True:
        pending.append("committed verification FAIL lines")
    if secret_decision is True:
        # The handout's confirmed-secret override resolves the final score.
        pending = []
    candidate_total = sum((r.score if r.score is not None else r.candidate) for r in rows.values())
    task1_score = sum((rows[code].score if rows[code].score is not None else rows[code].candidate)
                      for code in ("T1.1", "T1.2", "T1.3", "T1.4"))
    if gate == "missing":
        candidate_total -= max(0, task1_score - 12.5)
    candidate_total = round(candidate_total, 2)
    total = 0.0 if secret_decision is True else candidate_total
    final = secret_decision is True or not pending
    reviewer = review.get("reviewer")
    if reviewer is not None and (not isinstance(reviewer, str) or not reviewer.strip()):
        raise ValueError("reviewer must be a nonempty string")
    review_notes = review.get("review_notes", [])
    if not isinstance(review_notes, list) or not all(isinstance(note, str) and note.strip() for note in review_notes):
        raise ValueError("review_notes must be a list of nonempty strings")
    first_name = student.replace("_", " ").split()[0]
    status = "Proposed final — TA verification pending" if final and llm_review else "Final" if final else "Provisional — TA review required"
    lines = [f"# Lab 2 grade — {student}", "", f"Status: **{status}**",
             "", f"Score: **{fmt_points(total)}/100{' (provisional)' if not final else ''}**",
             "", "## Task summary", ""]
    if secret_decision is True:
        lines.append("The handout's confirmed-secret rule overrides all task points to 0/100.")
    else:
        for task, title, maximum, full_reason in TASKS:
            task_score = sum(
                rows[code].score if rows[code].score is not None else rows[code].candidate
                for code, _, _ in RUBRIC if code.startswith(f"T{task}.")
            )
            if task == 1 and gate == "missing":
                task_score = min(task_score, 12.5)
            result = full_reason if task_score == maximum else "See deductions below."
            if not final:
                result = "Candidate: " + result
            lines.append(f"- Task {task} — {title}: **{fmt_points(task_score)}/{maximum}**. {result}")

    lines += ["", "## Rubric breakdown", ""]
    deductions = []
    if secret_decision is True:
        lines.append("- Security override: confirmed committed secret (-100 points).")
    else:
        for code, title, _ in RUBRIC:
            row = rows[code]
            value = row.score if row.score is not None else row.candidate
            if value < row.maximum:
                reason = row.reasons[0] if row.reasons else "Criterion was not met"
                evidence = "; ".join(dict.fromkeys(row.evidence[:3]))
                detail = reason + (f" Evidence: {evidence}" if evidence else "")
                loss = fmt_points(row.maximum - value)
                lines.append(f"- **{code} — {title} (-{loss}):** {detail}")
                deductions.append(f"- {code}: {reason} (-{loss} points)")
        if gate == "missing" and task1_score > 12.5:
            loss = fmt_points(task1_score - 12.5)
            lines.append(f"- **Teardown cap (-{loss}):** Required post-submission evidence was not established; Task 1 is capped at 12.5/25.")
            deductions.append(f"- Teardown: Required post-submission evidence was not established; Task 1 is capped at 12.5/25 (-{loss} points)")
        if not deductions:
            lines.append("No rubric deductions.")

    lines += ["", "## Written work review", ""]
    for code, title, _ in RUBRIC:
        if code not in WRITTEN_CODES:
            continue
        row = rows[code]
        shown = fmt_points(row.score if row.score is not None else row.candidate)
        if row.score is None:
            shown += "*"
        explanation = "; ".join(row.reasons) or "No deduction identified"
        references = list(dict.fromkeys(row.evidence))
        more_specific = {re.sub(r":\d+$", "", ref) for ref in references if re.search(r":\d+$", ref)}
        evidence = "; ".join(ref for ref in references if ref not in more_specific)
        if evidence:
            explanation += f"{' ' if explanation.endswith('.') else '. '}Evidence: {evidence}"
        lines.append(f"- **{code} — {title}: {shown}/{fmt_points(row.maximum)}.** {explanation}")
    if any(row.score is None for row in rows.values()):
        lines += ["", "*Candidate score; item needs TA review.*"]
    lines += ["", "## Overrides and evidence", "",
              f"- Teardown: {gate} — {gate_evidence}.",
              f"- Secret review: {'confirmed; 0/100 override' if secret_decision is True else 'cleared' if secret_decision is False else 'pending'}."]
    if reviewer:
        lines.append(f"- Rubric review: {reviewer.strip()}.")
    lines.extend(f"- Review note: {note.strip()}" for note in review_notes)
    if fail_lines:
        locations = ", ".join(f"docs/lab2-verify-output.txt:{number}" for number in fail_lines[:12])
        lines.append(f"- Committed verifier: {len(fail_lines)} FAIL line(s) at {locations}" +
                     ("; additional lines omitted" if len(fail_lines) > 12 else "") + ".")
        if fail_reviewed is True:
            lines.append(f"- FAIL-line review: {fail_reason.strip()}")
    elif verify_passes is not None and verify_passes < 40:
        lines.append(f"- Committed verifier: {verify_passes} counted passes (older/partial format); individual FAIL lines were checked.")
    if candidates:
        lines.append("- Potential security findings (values redacted): " + "; ".join(candidates[:10]) + ("; …" if len(candidates) > 10 else ""))
    if pending:
        lines.append("- Pending review: " + ", ".join(pending) + ".")
    language_notes = diagnostics(root, files)
    if language_notes:
        lines += ["", "## Other static diagnostics", ""] + [f"- {note}" for note in language_notes]
    lines += ["", "## Canvas comment" + (" — draft; review before pasting" if not final or llm_review else ""), ""]
    if secret_decision is True:
        lines += [f"Hi {first_name},", "", "The submitted repository contains a confirmed committed secret. Under the Lab 2 handout, this results in 0/100. Please contact the course staff to address the exposed credential."]
    else:
        lines += [(f"Great work {first_name}" if total >= 85 else f"Hi {first_name},"), ""]
        if summary:
            lines += [summary, ""]
        if deductions:
            lines += ["Few things missing:", ""]
        elif not summary:
            lines += ["The submitted work met the reviewed rubric criteria.", ""]
        lines += deductions
        if pending:
            lines += ["", "[Draft: resolve the pending review items above before posting this comment.]"]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("submission", type=Path, help="one instructor student directory or the approved cs401r-jsims1 checkout")
    parser.add_argument("--student-id", help="output name; defaults to submission directory name")
    parser.add_argument("--review", type=Path, help="completed TA or LLM review JSON for final scores")
    parser.add_argument("--prepare-review", action="store_true", help="write an editable LLM review template beside the provisional grade")
    parser.add_argument("--output", type=Path, help="grade Markdown path (default: grades/<student_id>.md)")
    args = parser.parse_args()
    root = args.submission.resolve()
    try:
        inferred_student = submission_student_id(root)
    except ValueError as exc:
        parser.error(str(exc))
    student = args.student_id or inferred_student
    if not re.fullmatch(r"[A-Za-z0-9_-]+", student):
        parser.error("student-id must contain only letters, digits, underscore or hyphen")
    output = args.output or HERE / "grades" / f"{student}.md"
    if output.resolve() == root or root in output.resolve().parents:
        parser.error("output must not be inside the student submission")
    if args.prepare_review and args.review:
        parser.error("--prepare-review and --review cannot be used together")
    template_path = HERE / "reviews" / f"{student}.template.json"
    if args.prepare_review and template_path.exists():
        parser.error(f"review template already exists: {template_path}")
    try:
        analysis = analyze(root)
        template = review_template(student, analysis[1]) if args.prepare_review else None
        result = grade(root, student, load_review(args.review), analysis)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result, encoding="utf-8")
    if template is not None:
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    print(output)
    if template is not None:
        print(template_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
