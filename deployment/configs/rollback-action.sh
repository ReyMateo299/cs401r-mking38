#!/usr/bin/env bash
# Rollback: all traffic to champion. ~90 s; endpoint reads Updating but keeps serving.
# This stops the canary SERVING. It does not stop it BILLING. Only delete-endpoint does.
set -euo pipefail
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name northstar-churn-prod \
  --desired-weights-and-capacities \
    '[{"VariantName":"champion","DesiredWeight":10},{"VariantName":"canary","DesiredWeight":0}]'
aws sagemaker wait endpoint-in-service --endpoint-name northstar-churn-prod