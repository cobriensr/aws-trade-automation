# backend.tf
terraform {
  backend "s3" {
    bucket = "trading-terraform-state-jerseyse410"
    key    = "terraform.tfstate"
    region = "us-east-2"
  }
}