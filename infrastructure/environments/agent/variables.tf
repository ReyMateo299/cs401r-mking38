variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "northstar-agent"
}

variable "gateway_name" {
  type    = string
  default = "northstar-tools-gw"
}

variable "harness_name" {
  description = "Letters, digits, and underscores only; maximum 40 characters."
  type        = string
  default     = "northstar_agent"
}

variable "credit_cap_dollars" {
  description = "Largest loyalty credit allowed in one gateway call."
  type        = number
  default     = 50
}

variable "idle_session_timeout_seconds" {
  description = "Keep this low: AgentCore bills an idle runtime session."
  type        = number
  default     = 60
}

variable "max_session_lifetime_seconds" {
  type    = number
  default = 3600
}
