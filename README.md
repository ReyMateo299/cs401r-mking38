# NorthStar AI Platform

Infrastructure and data-pipeline work for CS 401R Labs 1 and 2. The platform
uses Terraform to provision AWS resources and Glue to convert raw customer
transactions into customer-level features for SageMaker Feature Store.

## Lab 1 foundation

Lab 1 establishes the reusable AWS foundation:

- `modules/vpc/` provisions the VPC, public subnet, internet gateway, and
  security group.
- `modules/storage/` provisions the versioned S3 data bucket.
- `modules/iam/` provisions the MLEngineer role.
- `modules/sagemaker/` provisions the SageMaker Studio domain.

The development environment composes those modules in
`infrastructure/environments/dev/`. For local Lab 1 validation, LocalStack
creates only the services it supports:

```bash
make local-validate LOCAL_OUT=docs/lab2-localstack-output.txt
```

To provision the development environment in AWS, configure AWS credentials for
`us-east-1`, then run:

```bash
terraform -chdir=infrastructure/environments/dev init
terraform -chdir=infrastructure/environments/dev plan
terraform -chdir=infrastructure/environments/dev apply
```

## Lab 2 additions

Lab 2 adds the data pipeline and its supporting resources:

- `modules/vpc/`, `modules/storage/`, `modules/iam/`, and
  `modules/sagemaker/` extend the Lab 1 foundation with a private subnet and
  NAT gateway, lifecycle rules, DataEngineer and ModelMonitor roles, and a
  VPC-only SageMaker domain.
- `modules/glue/` creates the Glue Data Catalog database, raw-data crawler,
  private-network Glue connection, and the transform and feature-engineering
  Spark jobs. It also uploads the scripts in `glue-scripts/` to S3 during
  Terraform apply.
- `modules/feature_store/` creates the SageMaker Feature Group with an online
  store and an S3-backed offline store.
- `glue-scripts/transform.py` cleans transaction data, enforces the processed
  schema, imputes missing values, and deduplicates on `transaction_id`.
- `glue-scripts/feature_engineer.py` creates one feature vector per customer.
  It computes features only through the feature cutoff and derives
  `churn_label` only from the later outcome window.

The data flow is:

```text
raw/customers/ (CSV)
  -> Glue Crawler and Catalog
  -> transform job
  -> processed/customers/ (Parquet, one row per transaction)
  -> feature engineering job
  -> features/customers/ (Parquet, one row per customer)
     + SageMaker Feature Store records
```

`DataEngineer` performs the Glue and Feature Store writes. `MLEngineer` reads
the feature data for later model-training labs.

## Run the data pipeline end to end

These commands run from the repository root after the development Terraform
apply succeeds. They use Terraform outputs so the bucket and Glue resource
names stay parameterized.

```bash
INFRA_DIR=infrastructure/environments/dev
BUCKET=$(terraform -chdir="$INFRA_DIR" output -raw s3_bucket_name)
CRAWLER=$(terraform -chdir="$INFRA_DIR" output -raw glue_crawler_name)
TRANSFORM_JOB=$(terraform -chdir="$INFRA_DIR" output -raw glue_transform_job_name)
FEATURE_JOB=$(terraform -chdir="$INFRA_DIR" output -raw glue_feature_engineer_job_name)
FEATURE_GROUP=$(terraform -chdir="$INFRA_DIR" output -raw feature_group_name)
```

1. Upload the supplied transaction data and create the catalog table.

   ```bash
   aws s3 cp northstar-raw-sample.csv "s3://$BUCKET/raw/customers/northstar-raw-sample.csv"
   aws glue start-crawler --name "$CRAWLER"
   aws glue wait crawler-ready --name "$CRAWLER"
   aws glue get-table --database-name northstar_dev --name customers
   ```

2. Transform CSV transactions into processed Parquet.

   ```bash
   TRANSFORM_RUN_ID=$(aws glue start-job-run --job-name "$TRANSFORM_JOB" --query JobRunId --output text)
   aws glue wait job-run-succeeded --job-name "$TRANSFORM_JOB" --run-id "$TRANSFORM_RUN_ID"
   aws s3 ls "s3://$BUCKET/processed/customers/" --recursive
   ```

3. Produce customer features and ingest them into Feature Store.

   ```bash
   FEATURE_RUN_ID=$(aws glue start-job-run --job-name "$FEATURE_JOB" --query JobRunId --output text)
   aws glue wait job-run-succeeded --job-name "$FEATURE_JOB" --run-id "$FEATURE_RUN_ID"
   aws s3 ls "s3://$BUCKET/features/customers/" --recursive
   aws sagemaker describe-feature-group --feature-group-name "$FEATURE_GROUP"
   ```

4. Run the Lab 2 verification script before submission.

   ```bash
   ./scripts/verify-lab2.sh
   ```

Glue jobs run inside the private subnet and need NAT egress. If a job fails,
inspect the run details in Glue and verify the DataEngineer role, VPC
connection, security-group self-reference rule, and NAT gateway before rerunning.

## Documentation

- `docs/lab2-data-contract.md` defines the `processed/customers/` contract.
- `docs/lab2-data-lineage.drawio` is the editable lineage diagram source; export
  it as `docs/lab2-data-lineage.png` for the Lab 2 deliverable.
