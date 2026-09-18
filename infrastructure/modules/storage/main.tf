# ── modules/storage ──────────────────────────────────────────────────────────
# Required resources (Task B1). Only these belong in this module:
#
#   aws_s3_bucket
#   aws_s3_bucket_public_access_block
#   aws_s3_bucket_versioning
#   aws_s3_bucket_server_side_encryption_configuration
#   aws_s3_object  x4                 the raw/ processed/ features/ artifacts/ prefixes
#
# ONE bucket with four prefixes, not four buckets. Later labs derive the name
# as ${project}-${environment}-data-${account_id}, so keep that shape.
#
# The four aws_s3_object resources create the prefixes. S3 has no real
# directories; an empty object with a trailing slash is how a prefix is made
# to exist before anything is written to it.


# ── modules/storage ──────────────────────────────────────────────────────────
# One bucket, four prefixes. The bucket name carries the account ID because S3
# names are global: every student would otherwise collide on
# northstar-dev-data. The account ID is read from the caller rather than
# passed in, so the module signature stays project + environment and the
# LocalStack environment (account 000000000000) needs no special casing.

data "aws_caller_identity" "current" {}

locals {
  bucket_name = "${var.project}-${var.environment}-data-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "data" {
  bucket = local.bucket_name

  # Versioning is on, so a plain destroy would fail with BucketNotEmpty once
  # anything has been written. Lab data is synthetic and regenerable, and the
  # course requires a full teardown after every lab, so the bucket opts in to
  # force_destroy. Never do this on a bucket holding real customer data.
  force_destroy = var.force_destroy

  tags = {
    Name = local.bucket_name
  }
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 has no directories. A zero-byte object whose key ends in "/" is what
# makes a prefix exist before anything is written under it, and it is what
# the console renders as a folder.
resource "aws_s3_object" "prefix" {
  for_each = toset(var.prefixes)

  bucket  = aws_s3_bucket.data.id
  key     = each.value
  content = ""
}
