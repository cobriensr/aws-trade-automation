# monitoring.tf

# Lambda function alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.name_prefix}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description = join("\n", [
    "Lambda function errors detected",
    "",
    "Function: ${aws_lambda_function.main.function_name}",
    "Log Group: ${aws_cloudwatch_log_group.lambda_logs.name}",
    "",
    "View logs at:",
    "https://console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#logsV2:log-groups/log-group/${aws_cloudwatch_log_group.lambda_logs.name}"
  ])
  alarm_actions      = [aws_sns_topic.alerts.arn]
  treat_missing_data = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = local.common_tags
}

# Cloudwatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = local.common_tags
}

# Lambda Throttling Alarm
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${local.name_prefix}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda function is being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = local.common_tags
}

# API Gateway 5XX Errors
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${local.name_prefix}-api-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "API Gateway is returning 5XX errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiId = aws_apigatewayv2_api.main.id
  }

  tags = local.common_tags
}

# KMS key for SNS encryption
resource "aws_kms_key" "sns" {
  description             = "KMS key for SNS topic encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow SNS to use the key"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "sns" {
  name          = "alias/${local.name_prefix}-sns"
  target_key_id = aws_kms_key.sns.key_id
}


# SNS Topic for Alerts with encryption
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

  kms_master_key_id = aws_kms_key.sns.id

  tags = local.common_tags
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "alerts_email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# High Latency Alert
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${local.name_prefix}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = "5000" # 5 seconds
  alarm_description   = "Lambda function taking too long to execute"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }
}

# Memory Usage Alert
resource "aws_cloudwatch_metric_alarm" "lambda_memory" {
  alarm_name          = "${local.name_prefix}-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MaxMemoryUsed"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "819"
  alarm_description   = "Lambda function approaching memory limit"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }
}

# Consecutive Message Processing Failures
resource "aws_cloudwatch_metric_alarm" "consecutive_failures" {
  alarm_name          = "${local.name_prefix}-consecutive-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConsecutiveFailures"
  namespace           = "Trading/Custom"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "2"
  alarm_description   = "Multiple consecutive message processing failures"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# Cloudwatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.main.function_name}"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = local.common_tags
}

# Lambda 2 CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda2_logs" {
  name              = "/aws/lambda/${aws_lambda_function.symbol_lookup.function_name}"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = local.common_tags
}

# Lambda 2 Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda2_errors" {
  alarm_name          = "${local.name_prefix}-lambda2-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda 2 function errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Lambda 2 Throttling Alarm
resource "aws_cloudwatch_metric_alarm" "lambda2_throttles" {
  alarm_name          = "${local.name_prefix}-lambda2-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda 2 (Symbol Lookup) function is being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Lambda 2 High Latency Alert
resource "aws_cloudwatch_metric_alarm" "lambda2_duration" {
  alarm_name          = "${local.name_prefix}-lambda2-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = "5000" # 5 seconds
  alarm_description   = "Lambda 2 (Symbol Lookup) taking too long to execute"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Lambda 2 Memory Usage Alert
resource "aws_cloudwatch_metric_alarm" "lambda2_memory" {
  alarm_name          = "${local.name_prefix}-lambda2-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MaxMemoryUsed"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "819"
  alarm_description   = "Lambda 2 (Symbol Lookup) approaching memory limit"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Lambda 2 Invocation Error Rate
resource "aws_cloudwatch_metric_alarm" "lambda2_error_rate" {
  alarm_name          = "${local.name_prefix}-lambda2-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AWS/Lambda"
  period              = "300" # 5 minutes
  statistic           = "Average"
  threshold           = "5" # 5% error rate
  alarm_description   = "Lambda 2 (Symbol Lookup) error rate exceeds 5%"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Lambda 2 Concurrent Executions
resource "aws_cloudwatch_metric_alarm" "lambda2_concurrent_executions" {
  alarm_name          = "${local.name_prefix}-lambda2-concurrent-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "50"
  alarm_description   = "Lambda 2 (Symbol Lookup) concurrent executions exceeding threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Monitor Lambda2 invocation failures
resource "aws_cloudwatch_metric_alarm" "lambda2_invocation_failures" {
  alarm_name          = "${local.name_prefix}-lambda2-invocation-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "SymbolLookupInvocationError"
  namespace           = "Trading/Custom"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Failures invoking Symbol Lookup Lambda"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  tags = local.common_tags
}

# Lambda 3 CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda3_logs" {
  name              = "/aws/lambda/${aws_lambda_function.coinbase.function_name}"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn

  tags = local.common_tags
}

# Lambda 3 Error Alarm
resource "aws_cloudwatch_metric_alarm" "lambda3_errors" {
  alarm_name          = "${local.name_prefix}-lambda3-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda 3 function errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}

# Lambda 3 Throttling Alarm
resource "aws_cloudwatch_metric_alarm" "lambda3_throttles" {
  alarm_name          = "${local.name_prefix}-lambda3-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda 3 (Symbol Lookup) function is being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}

# Lambda 3 High Latency Alert
resource "aws_cloudwatch_metric_alarm" "lambda3_duration" {
  alarm_name          = "${local.name_prefix}-lambda3-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = "5000" # 5 seconds
  alarm_description   = "Lambda 3 (Symbol Lookup) taking too long to execute"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}

# Lambda 3 Memory Usage Alert
resource "aws_cloudwatch_metric_alarm" "lambda3_memory" {
  alarm_name          = "${local.name_prefix}-lambda3-memory-usage"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MaxMemoryUsed"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "819"
  alarm_description   = "Lambda 3 (Symbol Lookup) approaching memory limit"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}

# Lambda 3 Invocation Error Rate
resource "aws_cloudwatch_metric_alarm" "lambda3_error_rate" {
  alarm_name          = "${local.name_prefix}-lambda3-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ErrorRate"
  namespace           = "AWS/Lambda"
  period              = "300" # 5 minutes
  statistic           = "Average"
  threshold           = "5" # 5% error rate
  alarm_description   = "Lambda 3 (Symbol Lookup) error rate exceeds 5%"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}

# Lambda 3 Concurrent Executions
resource "aws_cloudwatch_metric_alarm" "lambda3_concurrent_executions" {
  alarm_name          = "${local.name_prefix}-lambda3-concurrent-executions"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "50"
  alarm_description   = "Lambda 3 (Symbol Lookup) concurrent executions exceeding threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}

# Monitor Lambda3 invocation failures
resource "aws_cloudwatch_metric_alarm" "lambda3_invocation_failures" {
  alarm_name          = "${local.name_prefix}-lambda3-invocation-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "CoinbaseInvocationError"
  namespace           = "Trading/Custom"
  period              = "60"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Failures invoking Coinbase Lambda"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  tags = local.common_tags
}

# Create a CloudWatch log group for the flow logs
resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  name              = "/aws/vpc/${local.name_prefix}-vpc-flow-logs"
  retention_in_days = 7
  kms_key_id        = aws_kms_key.cloudwatch_logs.arn
  tags              = local.common_tags
}

# Main function high concurrency alarm
resource "aws_cloudwatch_metric_alarm" "lambda_high_concurrency" {
  alarm_name          = "${local.name_prefix}-high-concurrency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "8" # Alert at 8 concurrent executions
  alarm_description   = "Alert when trading function concurrency is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }

  tags = local.common_tags
}

# Symbol lookup function high concurrency alarm
resource "aws_cloudwatch_metric_alarm" "lambda2_high_concurrency" {
  alarm_name          = "${local.name_prefix}-lambda2-high-concurrency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "2" # Alert at 2 concurrent executions
  alarm_description   = "Alert when symbol lookup function concurrency is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}

# Coinbase function high concurrency alarm
resource "aws_cloudwatch_metric_alarm" "lambda3_high_concurrency" {
  alarm_name          = "${local.name_prefix}-lambda3-high-concurrency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Maximum"
  threshold           = "2" # Alert at 2 concurrent executions
  alarm_description   = "Alert when coinbase function concurrency is high"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.coinbase.function_name
  }

  tags = local.common_tags
}