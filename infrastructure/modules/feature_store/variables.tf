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