# ── modules/iam ──────────────────────────────────────────────────────────────
# Required resources (Task B1). Exactly one of each:
#
#   aws_iam_role                     MLEngineer, trusted by sagemaker.amazonaws.com
#   aws_iam_policy
#   aws_iam_role_policy_attachment
#
# Least privilege is graded in later labs, so start narrow: grant only the S3
# prefixes and SageMaker actions this role actually needs. A wildcard policy
# here will cost you points in Lab 2.

# ── modules/iam ──────────────────────────────────────────────────────────────
# Lab 1 ships one role: MLEngineer, the execution role SageMaker Studio and
# every training job assume. It is scoped to what the Lab 1 spec lists and
# nothing else:
#
#   SageMaker      training jobs, models, endpoints, model registry, MLflow App
#   S3             read/write artifacts/ and features/ only
#   CloudWatch     write logs under /aws/sagemaker/
#   ECR            pull training container images
#
# raw/ and processed/ are denied by omission. The verify script simulates
# s3:PutObject on raw/ and expects implicitDeny; a wildcard S3 statement here
# would pass Lab 1 and cost points in Lab 2.
#
# The bucket ARN is derived the same way modules/storage builds the bucket
# name, so this module needs only project + environment.

data "aws_caller_identity" "current" {}

locals {
  bucket_arn = "arn:aws:s3:::${var.project}-${var.environment}-data-${data.aws_caller_identity.current.account_id}"
}

resource "aws_iam_role" "ml_engineer" {
  name = "${var.project}-${var.environment}-MLEngineer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "${var.project}-${var.environment}-MLEngineer"
  }
}

resource "aws_iam_policy" "ml_engineer" {
  name        = "${var.project}-${var.environment}-MLEngineerPolicy"
  description = "MLEngineer least privilege: SageMaker training and serving, artifacts/ and features/ prefixes, logs, ECR pull"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SageMakerTrainingAndServing"
        Effect = "Allow"
        Action = [
          "sagemaker:CreateTrainingJob",
          "sagemaker:DescribeTrainingJob",
          "sagemaker:StopTrainingJob",
          "sagemaker:ListTrainingJobs",
          "sagemaker:CreateModel",
          "sagemaker:DescribeModel",
          "sagemaker:DeleteModel",
          "sagemaker:CreateEndpointConfig",
          "sagemaker:DescribeEndpointConfig",
          "sagemaker:DeleteEndpointConfig",
          "sagemaker:CreateEndpoint",
          "sagemaker:DescribeEndpoint",
          "sagemaker:UpdateEndpoint",
          "sagemaker:DeleteEndpoint",
          "sagemaker:ListEndpoints",
          "sagemaker:InvokeEndpoint",
          "sagemaker:AddTags",
          "sagemaker:ListTags"
        ]
        Resource = "*"
      },
      {
        # Studio itself runs as this role. Its UI has to describe the Domain
        # and user profile, list and describe apps and spaces, and create or
        # delete the JupyterLab app when you open Studio and shut it down, and
        # mint the presigned URL that launches an app in a new tab.
        # Without these the Studio page shows "Permissions not configured
        # correctly" and the Lab 1a "open Studio, then shut it down" step
        # cannot be done. Scoped to Studio resource types only.
        Sid    = "StudioSelfService"
        Effect = "Allow"
        Action = [
          "sagemaker:DescribeDomain",
          "sagemaker:ListDomains",
          "sagemaker:DescribeUserProfile",
          "sagemaker:ListUserProfiles",
          "sagemaker:DescribeSpace",
          "sagemaker:ListSpaces",
          "sagemaker:CreateSpace",
          "sagemaker:UpdateSpace",
          "sagemaker:DeleteSpace",
          "sagemaker:DescribeApp",
          "sagemaker:ListApps",
          "sagemaker:CreateApp",
          "sagemaker:DeleteApp",
          "sagemaker:CreatePresignedDomainUrl"
        ]
        Resource = [
          "arn:aws:sagemaker:*:*:domain/*",
          "arn:aws:sagemaker:*:*:user-profile/*",
          "arn:aws:sagemaker:*:*:space/*",
          "arn:aws:sagemaker:*:*:app/*"
        ]
      },
      {
        # Experiment tracking is the serverless MLflow App (no charge). The
        # MLflow Tracking Server (CreateMlflowTrackingServer, $0.60/hr) is
        # deliberately absent from this list.
        Sid    = "SageMakerMlflowApp"
        Effect = "Allow"
        Action = [
          "sagemaker:CreateMlflowApp",
          "sagemaker:DescribeMlflowApp",
          "sagemaker:ListMlflowApps",
          "sagemaker:CreatePresignedMlflowAppUrl"
        ]
        Resource = "*"
      },
      {
        Sid    = "SageMakerModelRegistry"
        Effect = "Allow"
        Action = [
          "sagemaker:CreateModelPackageGroup",
          "sagemaker:DescribeModelPackageGroup",
          "sagemaker:ListModelPackageGroups",
          "sagemaker:CreateModelPackage",
          "sagemaker:DescribeModelPackage",
          "sagemaker:ListModelPackages",
          "sagemaker:UpdateModelPackage"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3ArtifactsAndFeatures"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${local.bucket_arn}/artifacts/*",
          "${local.bucket_arn}/features/*"
        ]
      },
      {
        Sid    = "S3BucketList"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = local.bucket_arn
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/sagemaker/*"
      },
      {
        Sid    = "ECRPull"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ml_engineer" {
  role       = aws_iam_role.ml_engineer.name
  policy_arn = aws_iam_policy.ml_engineer.arn
}
