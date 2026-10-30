"""Lab 4 Task 3: write lineage onto a registered model package.

RegisterModel records only the artifact and a pointer to the metrics. The rest
is one hop away: the training job (its input channel and COMMIT_SHA) and the
metrics JSON that ModelMetrics points at. This copies them onto the package as
CustomerMetadataProperties, the one field UpdateModelPackage allows.

    .venv/bin/python3.11 scripts/lab4_lineage.py <version>
"""

import hashlib
import json
import sys

import boto3

GROUP = "northstar-churn-models"
METRIC_KEYS = ("auc_roc", "baseline_auc", "lift_ci_low", "lift_ci_high",
               "precision_top10", "recall_top10")


def split_s3(uri):
    bucket, _, key = uri[len("s3://"):].partition("/")
    return bucket, key


def main(version):
    sm, s3 = boto3.client("sagemaker"), boto3.client("s3")
    account = boto3.client("sts").get_caller_identity()["Account"]
    region = sm.meta.region_name
    arn = f"arn:aws:sagemaker:{region}:{account}:model-package/{GROUP}/{version}"
    pkg = sm.describe_model_package(ModelPackageName=arn)

    # .../artifacts/training/<job>/output/model.tar.gz -> the training job
    url = pkg["InferenceSpecification"]["Containers"][0]["ModelDataUrl"]
    parts = url.split("/")
    job = sm.describe_training_job(TrainingJobName=parts[parts.index("output") - 1])
    data_uri = job["InputDataConfig"][0]["DataSource"]["S3DataSource"]["S3Uri"]

    # The data "version": newest LastModified under the channel, plus a hash of
    # the sorted (key, ETag) list, which changes if any part file changes.
    bucket, prefix = split_s3(data_uri)
    objs = [o for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix)
            for o in page.get("Contents", [])]
    newest = max(o["LastModified"] for o in objs)
    digest = hashlib.sha256("\n".join(f"{o['Key']} {o['ETag']}" for o in
                                      sorted(objs, key=lambda o: o["Key"])).encode()).hexdigest()
    if newest > job["TrainingStartTime"]:
        print(f"WARNING: data under {data_uri} changed at {newest}, after training started "
              f"({job['TrainingStartTime']}). The feature job was re-run; the timestamp "
              f"and hash describe today's data, not what this model trained on.")

    metrics_uri = pkg["ModelMetrics"]["ModelQuality"]["Statistics"]["S3Uri"]
    metrics = json.loads(s3.get_object(**dict(zip(("Bucket", "Key"), split_s3(metrics_uri))))["Body"].read())

    meta = {
        "commit_sha": job["Environment"]["COMMIT_SHA"],
        "training_job": job["TrainingJobName"],
        "training_started": job["TrainingStartTime"].isoformat(),
        "training_data_s3_uri": data_uri,
        "training_data_last_modified": newest.isoformat(),
        "training_data_sha256": digest,
        "training_data_objects": str(len(objs)),
        "evaluation_metrics_s3_uri": metrics_uri,
        **{k: str(metrics[k]) for k in METRIC_KEYS if k in metrics},
    }
    existing = pkg.get("CustomerMetadataProperties") or {}
    sm.update_model_package(ModelPackageArn=arn, CustomerMetadataProperties={**existing, **meta})
    print(f"updated {arn}")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: lab4_lineage.py <model package version>")
    main(sys.argv[1])
