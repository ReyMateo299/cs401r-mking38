# Every variable needs a description — Task B1 grades this.

variable "project" {
  description = "Project name, used as the first element of every resource name"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "prefixes" {
  description = "Top-level S3 prefixes to create in the data bucket"
  type        = list(string)
  default     = ["raw/", "processed/", "features/", "artifacts/"]
}

variable "force_destroy" {
  description = "Allow terraform destroy to delete the bucket while it still holds object versions. Safe only because lab data is synthetic; never enable on real data."
  type        = bool
  default     = true
}

variable "enable_lifecycle_rules" {
  description = "Apply the Lab 2 S3 lifecycle rules. False for LocalStack"
  type        = bool
  default     = true
}

variable "raw_expiration_days" {
  description = "Days before current objects under raw/ are deleted."
  type        = number
  default     = 90
}

variable "datacapture_expiration_days" {
  description = "Days before current objects under datacapture/ are deleted."
  type        = number
  default     = 7
}
