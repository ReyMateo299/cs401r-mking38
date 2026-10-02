variable "project" {
  description = "Project name, used as the first element of every resource name"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the data bucket"
  type        = string
}

variable "data_engineer_role_arn" {
  description = "ARN of the DataEngineer role"
  type        = string
}

variable "scripts_dir" {
  description = "Local path to the Glue job scripts uploaded during apply"
  type        = string
}

variable "raw_table_name" {
  description = "Name assigned by the crawler to the raw customer table"
  type        = string
  default     = "customers"
}

variable "feature_group_name" {
  description = "Name of the SageMaker Feature Store group used by the feature engineering job"
  type        = string
}

variable "aws_region" {
  description = "AWS region for the Feature Store runtime client in the feature engineering job"
  type        = string
  default     = "us-east-1"
}

variable "glue_version" {
  description = "Glue version providing Spark 3.3 and Python 3.10"
  type        = string
  default     = "4.0"
}

variable "worker_type" {
  description = "Glue worker type for the Spark jobs"
  type        = string
  default     = "G.1X"
}

variable "number_of_workers" {
  description = "Number of Glue workers; two is the minimum for a Spark job"
  type        = number
  default     = 2
}

variable "job_timeout_minutes" {
  description = "Maximum Glue job runtime in minutes to prevent indefinite billing"
  type        = number
  default     = 20
}

variable "enable_vpc_connection" {
  description = "Whether to run Glue jobs in the private subnet through a VPC connection"
  type        = bool
  default     = true
}

variable "private_subnet_id" {
  description = "ID of the private subnet used by the Glue VPC connection"
  type        = string
  default     = null
}

variable "security_group_ids" {
  description = "Security groups for the Glue connection, including the self-referencing security group"
  type        = list(string)
  default     = []
}

variable "availability_zone" {
  description = "Availability Zone required by the Glue VPC connection"
  type        = string
  default     = "us-east-1a"
}
