# locals.tf
locals {
  name_prefix       = "${var.project_name}-${var.environment}"
  symbol_lookup_arn = "${aws_lambda_function.symbol_lookup.arn}:${aws_lambda_alias.symbol_lookup.name}"
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}