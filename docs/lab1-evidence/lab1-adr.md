## ADR-001: NorthStar Platform Foundation

### Status
Accepted

### Context
NorthStar Retail is establishing a unified cloud AI platform to power three interconnected customer retention workloads: (1) a weekly churn prediction model evaluating 100,000+ active customer accounts, (2) an automated offer generation engine that targets identified at-risk accounts with customized retention promotions, and (3) an LLM-powered customer service assistant handling support interactions. These three systems are tightly coupled: customer support chat logs and escalation frequencies directly inform churn risk feature tables, while churn risk scores trigger automated offer generation. Rather than creating fragmented, per-project infrastructure, NorthStar requires a shared platform foundation across networking, storage, identity, and machine learning development.

The governing constraint in Lab 1 is financial and architectural: operating under a strict course budget envelope ($150 credit across seven labs). Every architecture decision must maximize reproducibility and security isolation while preventing premature expenditure on idle cloud infrastructure before production pipelines and model training begin in subsequent labs.

### Decision

**1. Network Topology: Single Public Subnet with Security Group Isolation**
We provisioned a VPC (`10.0.0.0/16`) containing a single public subnet (`10.0.100.0/24`, `northstar-dev-public-1`) in availability zone `us-east-1a`, connected to the internet via an Internet Gateway (`northstar-dev-igw`). We intentionally did not deploy a NAT Gateway or private subnets for Lab 1. A managed NAT Gateway incurs a baseline charge of ~$32.40/month ($0.045/hour continuous base charge plus $0.045/GB data processing), which would consume over 20% of our $150 course budget before training begins in Lab 3. SageMaker Studio runs in this public subnet; inbound exposure is mitigated by security group `northstar-dev-sagemaker-sg`, which restricts inbound traffic strictly to `10.0.0.0/16` (blocking public ingress entirely) while the IGW provides necessary outbound connectivity for Studio to pull ECR container images and reach SageMaker API endpoints.

**2. Storage Architecture: Single Tiered S3 Bucket with Four Logical Prefixes**
We deployed a single S3 bucket (`northstar-dev-data-{account_id}`) partitioned into four discrete prefixes: `raw/`, `processed/`, `features/`, and `artifacts/`. The bucket enforces AES-256 server-side encryption (SSE-S3), bucket versioning for data lineage, and complete public access blocking. Single-bucket prefix segmentation enables unified governance while isolating data stages: POS transactions and raw support transcripts land in `raw/`, batch ETL jobs output cleaned tables to `processed/`, customer churn feature sets reside in `features/`, and SageMaker model weights and evaluation outputs serialize into `artifacts/`.

**3. Identity Model: Scoped MLEngineer IAM Execution Role**
We created the `northstar-dev-MLEngineer` IAM role assumed by SageMaker Studio user profiles. Following least-privilege principles, the policy restricts read/write access exclusively to the `features/*` and `artifacts/*` prefixes, grants read-only permissions for ECR container images, and grants CloudWatch logging permissions. The role explicitly denies write and read permissions to `raw/` and `processed/`, preventing ML engineers from modifying upstream customer transaction logs or ETL tables.

### Consequences

#### What this makes easy
- **Cost Minimization for Initial Development:** Eliminating the NAT Gateway saves ~$1.08/day ($32.40/month), preserving the $150 student credit for heavy SageMaker training compute and Bedrock API calls in Labs 3–5.
- **Auditable Data Lineage for Churn Models:** Versioned prefix partitioning gives the churn scoring model a clear audit trail from `features/` to resulting model checkpoints in `artifacts/`, avoiding state confusion across NorthStar's three workloads.
- **Controlled Blast Radius:** Scoping the `MLEngineer` role to `features/*` ensures that exploratory experimentation in SageMaker notebooks cannot corrupt the raw clickstream or support chat data stored in `raw/`.

#### What this makes harder
- **Prefix-Level IAM Policy Complexity:** Enforcing access control via prefix conditions (`s3:prefix`) requires granular resource ARN string-matching policies rather than simple bucket-level grants. As Data Engineering and Model Monitoring roles are added in Lab 2, IAM policy size approaches the 10 KB inline policy limit.
- **Public IP Exposure Constraint:** Because SageMaker Studio sits in a public subnet with an auto-assigned public IP, perimeter security relies entirely on the correctness of `northstar-dev-sagemaker-sg`. A misconfigured security group rule could expose the subnet to external scanning.
- **Single Availability Zone Failure Mode:** Confining the public subnet to `us-east-1a` leaves the development environment vulnerable to service disruptions within that specific AZ, providing zero automated failover.

#### What would cause you to revisit this decision
- **Introduction of AWS Glue ETL in Lab 2:** AWS Glue jobs reading raw POS data and writing to Feature Store should not run in public subnets with direct internet exposure. When Lab 2 introduces Glue and offline Feature Store synchronization, we will revisit the topology to add private subnets and a NAT Gateway (or VPC Gateway Endpoints for S3).
- **Scale to Production Churn Scoring (>100k Accounts):** When model inference transitions from interactive notebook experimentation to scheduled production batch transforms handling hundreds of thousands of customer records containing PII, compliance policies will mandate PrivateLink VPC Interface Endpoints for SageMaker APIs and full multi-AZ subnet deployment across at least two AZs (`us-east-1a` and `us-east-1b`).

### Alternative Considered
**Deploying Separate S3 Buckets for Each Data Tier (4 Buckets instead of 1).**
We considered provisioning four dedicated S3 buckets: `northstar-raw-data`, `northstar-processed-data`, `northstar-features`, and `northstar-artifacts`. This pattern provides clean IAM resource-level boundaries (allowing full bucket ARNs like `arn:aws:s3:::northstar-artifacts/*` without complex `Condition` statements on prefixes) and allows independent bucket encryption keys and lifecycle rules per tier.

We rejected this alternative because managing four distinct S3 buckets quadruples Terraform resource configuration, state locking overhead, and CloudTrail data event logging costs. Furthermore, in early development, having four separate buckets introduces cross-bucket inventory management complexity without providing meaningful security benefits over prefix-level IAM policies for a single engineering team.

### AWS Service Selection
- **Networking isolation model:** Amazon VPC because NorthStar requires isolated network boundaries and CIDR segmentation (`10.0.0.0/16`) to govern traffic access between SageMaker, future data pipelines, and external endpoints.
- **Storage design:** Amazon S3 because durable, versioned object storage with 99.999999999% durability is required to persist customer transactional history and model artifacts outside ephemeral compute instances.
- **Identity model:** AWS IAM because NorthStar requires granular role assumption and least-privilege policy evaluation to prevent unauthorized access across different stages of customer data.
- **ML development environment:** Amazon SageMaker Studio because it provides unified notebook compute, containerized runtime environments, and native integration with the NorthStar execution role and S3 feature store tiers.