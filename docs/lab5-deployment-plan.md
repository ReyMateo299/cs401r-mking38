# NorthStar Churn Model: Deployment Plan

Run from the repository root in `us-east-1`:

```bash
ACCT=$(aws sts get-caller-identity --query Account --output text)
EP=northstar-churn-prod
PKG=arn:aws:sagemaker:us-east-1:${ACCT}:model-package/northstar-churn-models/7
```

## 1. Deployment strategy and rationale

NorthStar scores every customer daily, with fresh scores due by 6 AM ET for that
day's retention campaign, and no system reads a churn score in real time. Batch
Transform is therefore the right production design: it bills only while the
nightly job runs, while an endpoint idles about 23 hours a day. This deployment
uses a real-time endpoint with a 9:1 canary anyway, because the lab's controls
(weighted traffic split, weight-based rollback, auto-scaling) exist only on
endpoints.

## 2. Pre-deployment checklist

Items 1–6 must be true before `create-endpoint`; item 7 once it is `InService`.

1. **The ML Lead has approved the package** against the gates: precision@10% ≥ 0.50, recall@10% ≥ 0.25, lift 95% CI excludes 0 (v7: 0.7167, 0.3258, [0.0455, 0.0839]):
   `aws sagemaker describe-model-package --model-package-name ${PKG} --query '[ModelApprovalStatus,ApprovalDescription]' --output text`
2. **The model artifact exists:**
   `aws s3 ls $(aws sagemaker describe-model-package --model-package-name ${PKG} --query 'InferenceSpecification.Containers[0].ModelDataUrl' --output text)`
3. **The MLEngineer role can write `datacapture/`**, and capture is enabled in the endpoint config (it cannot be edited later).
4. **The files in `deployment/configs/` exist:** endpoint config (9:1), alarm, scaling target and policy, `rollback-action.sh`, header-less `sample.csv`. Fill in the account:
   `sed "s/ACCOUNT_ID/${ACCT}/" deployment/configs/endpoint-config-canary-m5.json > /tmp/epc.json`
5. **The rollback alarm exists and is not in `ALARM`:**
   `aws cloudwatch put-metric-alarm --cli-input-json file://deployment/configs/rollback-alarm.json`
6. **Stakeholders are notified** (section 5).
7. **Each variant passes a smoke test** (repeat with `champion`):
   `aws sagemaker-runtime invoke-endpoint --endpoint-name ${EP} --content-type text/csv --target-variant canary --body fileb://deployment/configs/sample.csv /tmp/out.txt`

Champion and canary both serve v7, so this canary tests the deployment path and
cannot catch a model regression.

## 3. Rollback criteria

The alarm `northstar-churn-rollback-latency` (`deployment/configs/rollback-alarm.json`)
fires when the **canary's p95 `ModelLatency` exceeds 200,000 µs (200 ms) for 2
consecutive 1-minute periods**. The metric is in microseconds, so the threshold
is `200000`, not `200`. Measured steady state is about 4–7 ms and the cold start
about 24 ms, so it catches real regressions but not cold starts.

The ML Lead sets the criteria with the Retention Product Owner. The on-call ML
engineer makes the call and needs no approval. The alarm has no actions, so the
engineer watches it and rolls back when it enters `ALARM`, or on any canary 5XX
error, then informs the ML Lead:

```bash
bash deployment/configs/rollback-action.sh
```

This sets the canary's weight to 0 in about 90 seconds without dropped
requests.

## 4. Monitoring window

**Duration.** Production: 48 hours at 9:1 before the ML Lead promotes the
canary. Lab: 60 minutes (04:15–05:15 UTC, 2026-11-15).

**Watched.** Canary-only metrics (`VariantName=canary`), so the champion's 90%
of traffic cannot mask a problem: `ModelLatency`, `Invocation5XXErrors`,
`Invocations` and the alarm.

**Clean** means zero canary 5XX errors, latency under the threshold after the
cold start, the alarm `OK`, about 10% of calls reaching the canary, and capture
objects arriving for both variants. This run was clean: 0 errors, average
latency 3.2–4.5 ms (maximum 10 ms), 101 canary calls.

**What 60 minutes cannot catch:** a full daily traffic cycle and peak load; a
nightly feature refresh (POS data lands at 2 AM ET); a reliable p95 (about 100
canary calls is too few to see rare errors); slow degradation; and accuracy,
because churn labels arrive about 90 days after scoring.

## 5. Stakeholder notifications

The ML Lead sends the start and promotion notices; the on-call ML engineer sends
the rollback notice.

- **Start:** on-call ML engineer (monitoring window, rollback script); Retention Product Owner (canary at 10%, scores unchanged, no action); Data Platform Lead (capture writes to `datacapture/`); Privacy and Compliance Officer (capture is on, records expire after 7 days); Cloud Cost Owner (the endpoint bills about $0.23 per hour until deleted).
- **Promotion:** Retention Product Owner (the new model scores 100% of traffic, with its gate metrics); Data Platform Lead and on-call ML engineer (window closed, configuration changed); Executive Sponsor (one-line status).
- **Rollback:** ML Lead immediately (alarm time, metric value, canary at weight 0); Retention Product Owner (the champion is still scoring, campaigns unaffected); Executive Sponsor (summary within one business day).

## 6. Post-deployment review

Five business days after promotion (or after a rollback). Attendees: ML Lead
(chair), on-call ML engineer, Data Platform Lead, Privacy and Compliance
Officer, Retention Product Owner. It produces a one-page review, stored in the
repository, that updates the model card: approval metrics, window results, any
rollback and its cause, score distribution and campaign selection against the
previous model, cost, and the decision to keep or change the champion. It sets a date to re-check accuracy against actual churn.

## 7. Resource cleanup

Rolling back to weight 0 stops serving, not billing; only deleting the endpoint
stops the charge.
`bash scripts/teardown-lab5.sh` deletes, in order: scaling policies and target;
rollback alarms (`northstar-churn-rollback*`); the endpoint; endpoint configs,
then models (configs reference models); and in-progress transform or processing
jobs. It deletes every endpoint, config and model in the region.

Verify against the live API, not the console. The script writes
`docs/lab5-teardown-output.txt` (every line `OK`), and these must all print `0`:

```bash
aws sagemaker list-endpoints --query 'length(Endpoints)' --output text
aws sagemaker list-endpoint-configs --query 'length(EndpointConfigs)' --output text
aws application-autoscaling describe-scalable-targets --service-namespace sagemaker --query 'length(ScalableTargets)' --output text
```

Kept: Model Registry packages (free) and the evidence files; captured data
expires on its own. If the data platform is not needed next, run
`scripts/teardown-lab2.sh`.
