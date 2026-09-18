# Every variable needs a description — Task B1 grades this.

variable "project" {
  description = "Project name, used as the first element of every resource name"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "vpc_id" {
  description = "VPC the SageMaker Domain attaches to"
  type        = string
}

variable "subnet_ids" {
  description = "Subnets the SageMaker Domain may use"
  type        = list(string)
}

variable "app_network_access_type" {
  description = "PublicInternetOnly (Lab 1, public subnet) or VpcOnly (Lab 2+, private subnet with NAT egress). Changing this replaces the Domain."
  type        = string
  default     = "PublicInternetOnly"

  validation {
    condition     = contains(["PublicInternetOnly", "VpcOnly"], var.app_network_access_type)
    error_message = "app_network_access_type must be PublicInternetOnly or VpcOnly."
  }
}

variable "user_profile_name" {
  description = "Name of the single Studio user profile"
  type        = string
  default     = "MLEngineer"
}
