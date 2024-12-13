variable "terraform_state_bucket" {
  description = "Name of the S3 bucket for Terraform state"
  type        = string
}

variable "terraform_state_logs_bucket" {
  description = "Name of the S3 bucket for Terraform state access logs"
  type        = string
}