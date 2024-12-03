# variables.tf
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "trading"
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
  default     = "prod"
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = "jerseyse410@gmail.com"
}