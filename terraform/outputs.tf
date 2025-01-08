# outputs.tf
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "s3_kms_key_arn" {
  value       = aws_kms_key.s3.arn
  description = "The ARN of the KMS key used for S3 encryption"
}

output "lambda_function_config" {
  description = "Lambda function configuration"
  value = {
    function_name = aws_lambda_function.main.function_name
    arn          = aws_lambda_function.main.arn
    # Add other non-sensitive values you want to output
  }
  sensitive = true
}

output "symbol_lookup_function_config" {
  description = "Symbol lookup Lambda function configuration"
  value = {
    function_name = aws_lambda_function.symbol_lookup.function_name
    arn          = aws_lambda_function.symbol_lookup.arn
  }
  sensitive = true
}

output "coinbase_function_config" {
  description = "Coinbase Lambda function configuration"
  value = {
    function_name = aws_lambda_function.coinbase.function_name
    arn          = aws_lambda_function.coinbase.arn
  }
  sensitive = true
}