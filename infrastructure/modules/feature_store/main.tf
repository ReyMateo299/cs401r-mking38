# ── modules/feature_store ────────────────────────────────────────────────────
# One Feature Group, northstar-dev-customer-features: 2 keys, 13 features,
# 1 label. Online store for low-latency GetRecord (Labs 3-4), offline store in
# S3 for building training sets.
#
# event_time is Fractional (Unix epoch seconds), not String. Feature Store
# accepts either, but a mismatch between the declared type and the value the
# job writes makes PutRecord return success while the record never lands.
# The job writes float(timestamp); this declares Fractional.
#
# The offline store gets features/offline-store/, separate from the Parquet
# the feature engineering job writes to features/customers/. Feature Store
# manages its own directory tree under whatever prefix it is given.

resource "aws_sagemaker_feature_group" "customer_features" {
  feature_group_name             = "${var.project}-${var.environment}-customer-features"
  record_identifier_feature_name = "customer_id"
  event_time_feature_name        = "event_time"
  role_arn                       = var.data_engineer_role_arn
  description                    = "Customer-level churn features computed to T, plus churn_label from the holdout window"

  feature_definition {
    feature_name = "customer_id"
    feature_type = "String"
  }

  feature_definition {
    feature_name = "event_time"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "days_since_last_purchase"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "customer_tenure_days"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "purchase_frequency_30d"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "purchase_frequency_90d"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "purchase_frequency_180d"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "avg_order_value"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "total_spend_90d"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "total_lifetime_value"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "avg_basket_size_6m"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "category_diversity_score"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "online_to_store_ratio"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "loyalty_tier"
    feature_type = "String"
  }

  feature_definition {
    feature_name = "churn_risk_score"
    feature_type = "Fractional"
  }

  feature_definition {
    feature_name = "churn_label"
    feature_type = "Integral"
  }

  online_store_config {
    enable_online_store = true
  }

  offline_store_config {
    disable_glue_table_creation = false

    s3_storage_config {
      s3_uri = "s3://${var.s3_bucket_name}/features/offline-store/"
    }
  }

  tags = {
    Name = "${var.project}-${var.environment}-customer-features"
  }
}