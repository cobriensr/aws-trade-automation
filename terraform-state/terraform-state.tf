provider "aws" {
  region = "us-east-2"
}

# S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = var.terraform_state_bucket
}

# Enable versioning for rollback capability
resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for storing access logs of the Terraform state bucket
resource "aws_s3_bucket" "terraform_state_access_logs" {
  bucket = var.terraform_state_logs_bucket
}

# Enable versioning for the access logs bucket
resource "aws_s3_bucket_versioning" "terraform_state_access_logs" {
  bucket = aws_s3_bucket.terraform_state_access_logs.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable encryption for the access logs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_access_logs" {
  bucket = aws_s3_bucket.terraform_state_access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block public access for the access logs bucket
resource "aws_s3_bucket_public_access_block" "terraform_state_access_logs" {
  bucket = aws_s3_bucket.terraform_state_access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable logging for the Terraform state bucket
resource "aws_s3_bucket_logging" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  target_bucket = var.terraform_state_logs_bucket
  target_prefix = "terraform-state-logs/"
}