# Surface what later labs need. Lab 2 reads these from `terraform output`,
# and scripts/verify-lab1.sh reads ALL FIVE of them with `terraform output
# -raw`, so every one must exist (uncommented and wired) before you run it.

output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = module.vpc.public_subnet_id
}

output "private_subnet_id" {
  description = "ID of the private subnet"
  value       = module.vpc.private_subnet_id
}

output "nat_gateway_id" {
  description = "ID of the Nat Gateway"
  value       = module.vpc.nat_gateway_id
}

output "s3_bucket_name" {
  description = "Name of the data bucket"
  value       = module.storage.bucket_name
}

output "ml_engineer_role_arn" {
  description = "ARN of the MLEngineer role"
  value       = module.iam.ml_engineer_role_arn
}

output "data_engineer_role_arn" {
  description = "ARN of the DataEngineer role"
  value       = module.iam.data_engineer_role_arn
}

output "model_monitor_role_arn" {
  description = "ARN of the ModelMonitor role"
  value       = module.iam.model_monitor_role_arn
}

output "sagemaker_domain_id" {
  description = "ID of the SageMaker Domain"
  value       = module.sagemaker.domain_id
}

output "security_group_id" {
  description = "ID of the SageMaker security group"
  value       = module.vpc.security_group_id
}

output "sagemaker_domain_url" {
  description = "Studio URL"
  value       = module.sagemaker.domain_url
}

output "glue_database_name" {
  description = "Name of the Glue Data Catalog database"
  value       = module.glue.database_name
}

output "glue_crawler_name" {
  description = "Name of the raw customer data crawler"
  value       = module.glue.crawler_name
}

output "glue_transform_job_name" {
  description = "Name of the Glue transform job"
  value       = module.glue.transform_job_name
}

output "glue_feature_engineer_job_name" {
  description = "Name of the Glue feature engineering job"
  value       = module.glue.feature_engineer_job_name
}

output "feature_group_name" {
  description = "Name of the SageMaker feature group"
  value       = module.feature_store.feature_group_name
}
