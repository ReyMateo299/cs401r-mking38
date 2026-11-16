# NorthStar Churn Model: Security and Privacy Assessment

## 1. STRIDE threat model

Scope: the churn model's data (Lab 2 bucket), the Model Registry package, and the
real-time endpoint `northstar-churn-prod`. The three Lab 2 roles are `MLEngineer`
(SageMaker training and serving, `artifacts/`, `features/` and `datacapture/`),
`DataEngineer` (Glue and the `raw/`, `processed/` and `features/` prefixes) and
`ModelMonitor` (CloudWatch and read-only `artifacts/`).

| Threat | STRIDE category | Likelihood | Impact | Mitigation | AWS control |
|---|---|---|---|---|---|
| T1. `DataEngineer` credentials are stolen or misused, and the attacker rewrites `features/` or `processed/` to poison the next training run | Tampering | M | H | **The role contains the damage:** `DataEngineer` can write only `raw/`, `processed/` and `features/`, and has no `artifacts/` write and no endpoint actions, so poisoned data cannot reach production directly. Detect and undo: the CI data and feature tests run before training, and versioning restores earlier objects. The metric gates are a detective control only; a subtle poisoning could still pass them. | IAM role `DataEngineer` with prefix-scoped S3 policy; S3 versioning (feature versions kept 60 days); CodeBuild `pre_build` tests (`tests/test_data.py`, `tests/test_features.py`) |
| T2. A caller with invoke access queries the endpoint repeatedly to infer whether a customer was in the training data (membership inference) or to copy the model | Information disclosure | M | H | **A gap the roles do not close:** none of the three roles limits who may call `InvokeEndpoint`, and `MLEngineer` holds it on every resource. Grant `sagemaker:InvokeEndpoint` only on the endpoint's ARN and only to the calling application's role, return the score and nothing else, and alarm on abnormal call volume. | IAM resource-level permission on `sagemaker:InvokeEndpoint`; CloudWatch alarm on `Invocations` (anomaly detection) |
| T3. A flood of calls, or a bad scaling setting, pushes auto-scaling to its maximum so the endpoint costs far more than planned (economic denial of service) | Denial of service | M | M | `MaxCapacity` in `scalable-target.json` caps the instance count at 4, and the account's `ml.m5.large` endpoint quota is a hard ceiling above that. Add a budget alert so a spike is seen the same day, and throttle callers. | Application Auto Scaling (`MaxCapacity`); Service Quotas (`L-614B09FD`); AWS Budgets |
| T4. One role can register, approve and deploy: the `MLEngineer` policy grants `CreateModelPackage` and `UpdateModelPackage` (approval) and `CreateEndpoint` and `UpdateEndpoint` (deployment), so one compromised or careless identity can push an unreviewed model to production | Elevation of privilege | M | H | **A gap the roles do not close.** Separate the duties: a new `ModelDeployer` role gets the endpoint actions, a separate approver role gets `UpdateModelPackage`, and `MLEngineer` keeps only `CreateModelPackage`. Deployment then requires an approved package that someone else approved. | IAM roles and policies (new `ModelDeployer` role); SageMaker Model Registry approval status |
| T5. Leaked AWS credentials, for example committed to this public repository, let an attacker act as a deployer or an endpoint caller | Spoofing | M | H | `.gitignore` excludes `.env`, `*.tfvars` and `*.tfstate`, and `scripts/check-secrets.sh` scans every commit. Use short-lived credentials and MFA instead of long-lived access keys. | `.gitignore` and `check-secrets.sh`; AWS STS temporary credentials; IAM MFA |
| T6. No reliable record of who approved a model, deployed it or called the endpoint: the approval description can be edited, and this repo configures no audit trail | Repudiation | M | M | Enable a CloudTrail trail for management events, with log file validation, to a separate bucket. Require the approver's role in every approval description. | AWS CloudTrail (log file validation); Model Registry `ApprovalDescription` |
| T7. Captured requests and scores under `datacapture/` are read by someone who should not see customer-derived data | Information disclosure | L | M | Only the endpoint's execution role can write `datacapture/`, and no Lab 2 role can read it. Objects are hidden after 7 days and deleted a day later by the lifecycle rule. Move the bucket to SSE-KMS for a separate key policy and a decrypt audit trail; it uses SSE-S3 today. | S3 lifecycle rule `expire-datacapture`; IAM prefix scoping; SSE-KMS |

Rows T1 (blast radius contained by `DataEngineer`) and T2 and T4 (gaps the
roles do not close) cover the role requirement.

## 2. Data classification

This table classifies NorthStar's data assets as described in the Lab 1 schema;
the churn platform itself ingests only the transaction extract (section 3.1).
Tiers: Public, Internal, Confidential, Restricted. Today the data bucket uses
SSE-S3 (`AES256`) for every prefix. A customer-managed SSE-KMS key adds a key
policy separate from the bucket policy, a CloudTrail record of every `Decrypt`,
and rotation; the choice per asset below says whether that is worth it.

| Asset | Tier | Encryption and reason | IAM access policy | Share with a third-party vendor |
|---|---|---|---|---|
| Product catalog (`product_catalog.json`: SKU, name, category, price, sale price, in-stock flag, rating, description) | Public | SSE-S3. It is published storefront data with no customer data, so it does not need a separate key policy or a `Decrypt` audit trail. Versioning protects its integrity. | Read-only for platform roles; written only by `DataEngineer` | Yes |
| Model weights (`model.tar.gz` under `artifacts/`) | Confidential | SSE-KMS with a customer-managed key (today SSE-S3, so the bucket default and the key policy must change). The weights encode customer behaviour and can be probed or copied (threat T2), so a key policy separate from the bucket policy, a `Decrypt` audit trail and rotation are worth the cost. | `MLEngineer` read and write on `artifacts/*`; `ModelMonitor` read-only on `artifacts/*`; `DataEngineer` none | No, except under contract after a security review |
| Customer PII (`customers.csv`: hashed email, age band, state, zip code, loyalty tier) | Restricted | SSE-KMS. Privacy law governs how it is processed, so a separate key policy and a `Decrypt` audit trail are worth the cost. Raw email is never stored; it is already hashed. | `DataEngineer` read and write on `raw/*` and `processed/*`; `MLEngineer` none | No |
| Transaction history (`transactions.parquet`, keyed by `customer_id`) | Restricted | SSE-KMS. Every purchase is tied to a customer, so it is personal data under the same laws. SSE-S3 would let anyone with bucket access read it; KMS adds a key policy and a `Decrypt` audit trail. | `DataEngineer` read and write on `raw/*` and `processed/*`; `MLEngineer` none | No |
| Behavioral clickstream (`clickstream.parquet`; `customer_id` is null for about 35% of events) | Restricted | SSE-KMS. A browsing history linked to a customer is personal data, so reads need a key policy and a `Decrypt` audit trail, which SSE-S3 does not give. Anonymous sessions alone would be Confidential, but the file mixes both, so it takes the higher tier. | `DataEngineer` read and write on `raw/*` and `processed/*`; `MLEngineer` none | No |
| Inference logs (`datacapture/`: the 11 feature values sent to the endpoint and the score returned) | Confidential | SSE-KMS, so reads of scores that can be matched to customers leave a `Decrypt` record. The records carry no `customer_id`, but behavioral features can be matched back to a customer through the Feature Store, and a churn score is personal data once matched. It would become Restricted if a caller added `customer_id` to the request. | `MLEngineer` (the endpoint's role) write-only on `datacapture/*`; no Lab 2 role can read it | No |
| Feature Store records (Feature Group `northstar-dev-customer-features`: 13 features and a label per `customer_id`, in the offline store at `features/` and the online store) | Confidential | SSE-KMS, because the features are keyed by `customer_id` and reads need an audit trail that SSE-S3 does not give. They are aggregates, not raw events, and hold no direct identifier, but they are derived from personal behavior. | `DataEngineer` read and write on `features/*` and Feature Store write; `MLEngineer` read and write on `features/*` | No, except aggregated and anonymized under contract |

## 3. Privacy impact assessment

### 3.1 Personal data inventory

The churn platform ingests one source: a transaction extract
(`northstar-raw-sample.csv`, one row per transaction). NorthStar's source systems
hold more (the CRM, clickstream and store events), but none of that enters this
platform.

| Pipeline stage | Where | Personal data processed |
|---|---|---|
| Ingest | `raw/customers/` | Nine fields per transaction: `transaction_id`, `customer_id`, `purchase_date`, `order_value`, `num_items`, `payment_method` (the type), `channel`, `store_id`, `product_category`. |
| Processing | `processed/customers/` | The same nine fields, cleaned and typed, with missing values imputed, still keyed by `customer_id`. |
| Feature engineering | `features/`, Feature Store (offline and online) | Per-customer aggregates derived from purchase history: recency, 30, 90 and 180-day purchase counts, average order value, spend, lifetime value, basket size, category diversity, online-to-store ratio, tenure, and the churn label. |
| Training | Training job, Model Registry | The 11 model features and the churn label for every customer. The trained weights encode patterns from this data but hold no record of any one customer. |
| Serving | Endpoint, `datacapture/` | The 11 feature values sent for scoring and the churn score returned. No `customer_id` is sent, but the features can be matched back to a customer. |

`customer_id` is a pseudonymous identifier: it is not a name, but it links all of
a customer's transactions and NorthStar can map it to a person, so it is
personal data. No names, emails, addresses, ages, zip codes, search text or
SKU-level data enter the platform, and there is no special-category data.

### 3.2 Lawful basis

**Legitimate interests** (GDPR Article 6(1)(f)). It passes the three-part test:

- **Purpose.** NorthStar has a genuine commercial interest in keeping customers: scoring lets it send a retention offer to customers likely to lapse.
- **Necessity.** The model uses 11 aggregates of purchase history and no identifying fields beyond the pseudonymous `customer_id`, so the processing is no wider than the purpose needs (section 3.3).
- **Balancing.** The data is purchase history the customers generated by shopping, and a loyalty customer reasonably expects retention marketing. The impact is low: a score leads to at most one retention offer per week and no decision with legal effect. Safeguards reduce the impact further: restricted access, encryption, retention limits and the suppression list (section 3.4).

Customers can **object** under Article 21. An objection puts the customer on the
suppression list, and the pipeline excludes them from then on.

Contractual necessity is weaker: scoring for retention is not necessary to
perform a sale. Consent would work, but it can be withdrawn at any time, which
would need the same suppression list and a retrain without those customers.

### 3.3 Data minimization

**Considered and excluded.** The churn platform never ingests these, although
NorthStar's source systems hold them:

- **Raw email** (the CRM stores it hashed, and it is not ingested).
- **Free-text search queries**, which customers sometimes fill with email addresses.
- **SKU-level detail.** Only `product_category` is ingested, and the model uses a category diversity score.
- **Precise location.** Only `store_id` is ingested, which identifies a store and not where the customer is. Zip code and state are not ingested.
- **Age band and clickstream events**, which the model does not need.

The model reduces the nine ingested fields to 11 aggregate features, with no
free text and no direct identifier.

**Remaining gaps.**
- `payment_method` and `store_id` are ingested and kept in `processed/`, but no feature uses them. Dropping them in the Glue transform would tighten this.
- The Feature Group also defines `loyalty_tier` and `churn_risk_score`, which the model does not use.
- Raw transactions expire after 90 days (the `expire-raw-data` lifecycle rule), which limits how long the unused fields are kept there.

### 3.4 Right to erasure

NorthStar receives a deletion request for `customer_id = C00123456`. First, the ID
goes on a suppression list that every pipeline run reads, so the next raw
extract cannot bring the customer back. Then, for each store:

- **(a) Raw S3 (`raw/`, `processed/`).** The bucket is versioned, so deleting rows
  is not enough. A Glue job rewrites each affected file without the customer's
  rows. Then every earlier version of those objects is permanently deleted:
  `aws s3api list-object-versions` for the keys, then `aws s3api delete-objects`
  with each `VersionId` and delete marker.
- **(b) Feature Store.** The online store supports `DeleteRecord`, which removes the
  customer's current record. The offline store is append-only Parquet in S3:
  `DeleteRecord` writes a tombstone and the history stays. So the offline files
  are rebuilt from the cleaned `processed/` data by rerunning the Glue feature
  job, and the old versions are deleted as in (a).
- **(c) Model training data.** The next training set is built from the rebuilt
  features, so it excludes the customer. The model is then retrained on it.
- **(d) Inference logs (`datacapture/`).** The captured records carry no
  `customer_id`, so they cannot be searched for one customer. The control is
  retention: objects are hidden after 7 days and permanently deleted a day later
  by the lifecycle rule, so the customer's captured scores are gone within 8
  days of the request.

**The hardest step is the trained model.** The customer's influence is spread
through the weights, and there is no delete operation for it. The only remedy is
to retrain without the customer, validate the new model, roll it out by canary,
and reject the earlier model versions in the Model Registry and delete their
artifacts. That is slow and costly, and one request cannot justify it alone.

**Batching.** Steps (a), (b) and (d) run promptly for each request. The retrain
is batched: requests are collected and handled together in the next scheduled
retrain. The batch interval must respect the legal deadline. GDPR Article 12(3)
requires a response without undue delay and within one month, extendable by two
further months only for complex or numerous requests, with notice to the
customer. So the retrain cycle should be about monthly, not every few months,
and the plan should document the lag between the request and the model that no
longer reflects the customer.

