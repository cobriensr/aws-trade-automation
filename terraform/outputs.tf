# outputs.tf
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "s3_kms_key_arn" {
  value       = aws_kms_key.s3.arn
  description = "The ARN of the KMS key used for S3 encryption"
}