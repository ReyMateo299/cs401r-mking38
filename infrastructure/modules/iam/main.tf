data "aws_caller_identity" "current" {}

locals {
  bucket_arn = "arn:aws:s3:::${var.project}-${var.environment}-data-${data.aws_caller_identity.current.account_id}"
}

# -- MLEngineer ---------------------------------------------------------------
#
#   SageMaker      training jobs, models, endpoints, model registry, MLflow App
#   S3             read/write artifacts/ and features/ only
#   CloudWatch     write logs under /aws/sagemaker/
#   ECR            pull training container images
#
# raw/ and processed/ are denied by omission. The verify script simulates
# s3:PutObject on raw/ and expects implicitDeny.

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

# ── DataEngineer (Lab 2) ─────────────────────────────────────────────────────
# Execution role for the Glue crawler, both Glue jobs, and the Feature Group.
#
#   Glue           catalog, crawler, and job APIs, plus GetConnection (the job
#                  resolves its NETWORK connection before the script runs)
#   EC2            ENI lifecycle for VPC-attached jobs, plus CreateTags /
#                  DeleteTags on network interfaces (Glue tags every ENI)
#   S3             read/write raw/ processed/ features/; read-only artifacts/glue/
#                  (its own job scripts); GetBucketAcl on the bucket and
#                  PutObjectAcl on features/ for the Feature Store offline store
#   Feature Store  PutRecord, CreateFeatureGroup, DescribeFeatureGroup
#   CloudWatch     write logs under /aws-glue/
#
# Cannot write artifacts/ (models are MLEngineer's) and cannot run SageMaker
# training. The trust policy includes sagemaker.amazonaws.com because
# CreateFeatureGroup rejects an execution role that does not trust SageMaker,
# even though this is otherwise a pure data-plane identity.

resource "aws_iam_role" "data_engineer" {
  name = "${var.project}-${var.environment}-DataEngineer"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = {
        Service = [
          "glue.amazonaws.com",
          "lambda.amazonaws.com",
          "sagemaker.amazonaws.com"
        ]
      }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "${var.project}-${var.environment}-DataEngineer"
  }
}

resource "aws_iam_policy" "data_engineer" {
  name        = "${var.project}-${var.environment}-DataEngineerPolicy"
  description = "DataEngineer least privilege: Glue ETL, raw/ processed/ features/ prefixes, Feature Store writes"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GlueCatalogCrawlerAndJobs"
        Effect = "Allow"
        Action = [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:CreateDatabase",
          "glue:UpdateDatabase",
          "glue:DeleteDatabase",
          "glue:GetTable",
          "glue:GetTables",
          "glue:CreateTable",
          "glue:UpdateTable",
          "glue:DeleteTable",
          "glue:GetPartition",
          "glue:GetPartitions",
          "glue:CreatePartition",
          "glue:UpdatePartition",
          "glue:BatchCreatePartition",
          "glue:GetCrawler",
          "glue:StartCrawler",
          "glue:StopCrawler",
          "glue:GetCrawlerMetrics",
          "glue:GetJob",
          "glue:GetJobs",
          "glue:StartJobRun",
          "glue:GetJobRun",
          "glue:GetJobRuns",
          "glue:BatchStopJobRun",
          "glue:GetConnection",
          "glue:GetConnections"
        ]
        Resource = "*"
      },
      {
        Sid    = "S3DataPrefixesReadWrite"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${local.bucket_arn}/raw/*",
          "${local.bucket_arn}/processed/*",
          "${local.bucket_arn}/features/*"
        ]
      },
      {
        Sid      = "S3GlueScriptsReadOnly"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${local.bucket_arn}/artifacts/glue/*"]
      },
      {
        # Feature Store checks the bucket ACL before accepting it as an
        # offline store target; without GetBucketAcl CreateFeatureGroup fails
        # with the misleading "Invalid S3Uri provided".
        Sid    = "S3BucketListAndAcl"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:GetBucketAcl"
        ]
        Resource = local.bucket_arn
      },
      {
        # The offline store writes objects with an ACL; plain PutObject is
        # not enough.
        Sid    = "FeatureStoreOfflineWrite"
        Effect = "Allow"
        Action = [
          "s3:PutObjectAcl",
          "s3:GetObjectAcl"
        ]
        Resource = "${local.bucket_arn}/features/*"
      },
      {
        Sid    = "FeatureStoreWrite"
        Effect = "Allow"
        Action = [
          "sagemaker:PutRecord",
          "sagemaker:CreateFeatureGroup",
          "sagemaker:DescribeFeatureGroup",
          "sagemaker:ListFeatureGroups"
        ]
        Resource = "*"
      },
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws-glue/*"
      },
      {
        Sid    = "GlueVpcNetworking"
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DeleteNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSubnets",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeVpcEndpoints",
          "ec2:DescribeRouteTables",
          "ec2:DescribeVpcAttribute",
          "ec2:DescribeDhcpOptions"
        ]
        Resource = "*"
      },
      {
        Sid    = "GlueEniTagging"
        Effect = "Allow"
        Action = [
          "ec2:CreateTags",
          "ec2:DeleteTags"
        ]
        Resource = "arn:aws:ec2:*:*:network-interface/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "data_engineer" {
  role       = aws_iam_role.data_engineer.name
  policy_arn = aws_iam_policy.data_engineer.arn
}

# ── ModelMonitor (Lab 2) ─────────────────────────────────────────────────────
# Observes; never acts. CloudWatch metrics and alarms, read-only visibility
# into processing jobs, read-only artifacts/, logs. No S3 write of any kind,
# no endpoint invocation, no ability to start a job. Lab 6 runs the drift
# analysis under a separate execution role; this one only watches.

resource "aws_iam_role" "model_monitor" {
  name = "${var.project}-${var.environment}-ModelMonitor"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "sagemaker.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = {
    Name = "${var.project}-${var.environment}-ModelMonitor"
  }
}

resource "aws_iam_policy" "model_monitor" {
  name        = "${var.project}-${var.environment}-ModelMonitorPolicy"
  description = "ModelMonitor least privilege: CloudWatch metrics and alarms, read-only artifacts/, read-only processing job visibility"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchMetricsAndAlarms"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:GetMetricData",
          "cloudwatch:ListMetrics",
          "cloudwatch:PutMetricAlarm",
          "cloudwatch:DescribeAlarms"
        ]
        Resource = "*"
      },
      {
        Sid    = "ProcessingJobReadOnly"
        Effect = "Allow"
        Action = [
          "sagemaker:ListProcessingJobs",
          "sagemaker:DescribeProcessingJob"
        ]
        Resource = "*"
      },
      {
        Sid      = "S3ArtifactsReadOnly"
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = ["${local.bucket_arn}/artifacts/*"]
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
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:log-group:/aws/sagemaker/*"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "model_monitor" {
  role       = aws_iam_role.model_monitor.name
  policy_arn = aws_iam_policy.model_monitor.arn
}
