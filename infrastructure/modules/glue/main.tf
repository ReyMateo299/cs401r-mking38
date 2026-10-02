# ── modules/glue ─────────────────────────────────────────────────────────────
# Catalog database, raw crawler, and the two ETL jobs (Lab 2).
#
#   raw/customers/  --crawler-->  northstar_dev.customers
#                                        |
#                                   transform job
#                                        v
#                              processed/customers/  (Parquet, transaction grain)
#                                        |
#                                feature-engineer job
#                                        v
#                    features/customers/ (Parquet, customer grain) + Feature Store
#
# Both jobs run inside the private subnet through a NETWORK connection, so
# they get NAT egress and never a public IP. The three provisioning-time
# failures that path produces (GetConnection, self-referencing SG rule, ENI
# tagging) are handled in modules/iam and modules/vpc.

resource "aws_glue_catalog_database" "this" {
  name        = replace("${var.project}_${var.environment}", "-", "_")
  description = "NorthStar data catalog: tables discovered by the crawler and written by ETL jobs"
}

resource "aws_glue_connection" "vpc" {
  count = var.enable_vpc_connection ? 1 : 0

  name            = "${var.project}-${var.environment}-vpc-connection"
  connection_type = "NETWORK"

  physical_connection_requirements {
    availability_zone      = var.availability_zone
    subnet_id              = var.private_subnet_id
    security_group_id_list = var.security_group_ids
  }
}

resource "aws_glue_crawler" "raw" {
  name          = "${var.project}-${var.environment}-raw-crawler"
  role          = var.data_engineer_role_arn
  database_name = aws_glue_catalog_database.this.name
  description   = "Scans raw/customers/ and registers the customers table"

  s3_target {
    path = "s3://${var.s3_bucket_name}/raw/customers/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  tags = {
    Name = "${var.project}-${var.environment}-raw-crawler"
  }
}

# Scripts are uploaded as part of apply so code and infrastructure move
# together. etag forces a re-upload whenever the file changes on disk.
resource "aws_s3_object" "transform_script" {
  bucket = var.s3_bucket_name
  key    = "artifacts/glue/transform.py"
  source = "${var.scripts_dir}/transform.py"
  etag   = filemd5("${var.scripts_dir}/transform.py")
}

resource "aws_s3_object" "feature_engineer_script" {
  bucket = var.s3_bucket_name
  key    = "artifacts/glue/feature_engineer.py"
  source = "${var.scripts_dir}/feature_engineer.py"
  etag   = filemd5("${var.scripts_dir}/feature_engineer.py")
}

resource "aws_glue_job" "transform" {
  name              = "${var.project}-${var.environment}-transform"
  role_arn          = var.data_engineer_role_arn
  description       = "Casts types, imputes nulls, and deduplicates transactions into processed/customers/"
  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  timeout           = var.job_timeout_minutes

  connections = var.enable_vpc_connection ? [aws_glue_connection.vpc[0].name] : []

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${var.s3_bucket_name}/${aws_s3_object.transform_script.key}"
  }

  default_arguments = {
    "--job-language"        = "python"
    "--job-bookmark-option" = "job-bookmark-disable"
    "--enable-metrics"      = "true"
    # TempDir sits under processed/ because DataEngineer is read-only on
    # artifacts/; a temp dir there would fail at runtime.
    "--TempDir"       = "s3://${var.s3_bucket_name}/processed/_glue_temp/"
    "--database_name" = aws_glue_catalog_database.this.name
    "--table_name"    = var.raw_table_name
    "--output_path"   = "s3://${var.s3_bucket_name}/processed/customers/"
  }

  tags = {
    Name = "${var.project}-${var.environment}-transform"
  }
}

resource "aws_glue_job" "feature_engineer" {
  name              = "${var.project}-${var.environment}-feature-engineer"
  role_arn          = var.data_engineer_role_arn
  description       = "Aggregates processed transactions into customer-level features and ingests them into Feature Store"
  glue_version      = var.glue_version
  worker_type       = var.worker_type
  number_of_workers = var.number_of_workers
  timeout           = var.job_timeout_minutes

  connections = var.enable_vpc_connection ? [aws_glue_connection.vpc[0].name] : []

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${var.s3_bucket_name}/${aws_s3_object.feature_engineer_script.key}"
  }

  default_arguments = {
    "--job-language"        = "python"
    "--job-bookmark-option" = "job-bookmark-disable"
    "--enable-metrics"      = "true"
    "--TempDir"             = "s3://${var.s3_bucket_name}/processed/_glue_temp/"
    "--input_path"          = "s3://${var.s3_bucket_name}/processed/customers/"
    "--output_path"         = "s3://${var.s3_bucket_name}/features/customers/"
    "--feature_group_name"  = var.feature_group_name
    "--region"              = var.aws_region
  }

  tags = {
    Name = "${var.project}-${var.environment}-feature-engineer"
  }
}