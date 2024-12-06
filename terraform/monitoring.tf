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

# SNS Topic for Alerts
resource "aws_sns_topic" "alerts" {
  name = "${local.name_prefix}-alerts"

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
  threshold           = "819" # 80% of 1024MB
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
}

# Lambda 2 CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda2_logs" {
  name              = "/aws/lambda/${aws_lambda_function.symbol_lookup.function_name}"
  retention_in_days = 7

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
  statistic          = "Sum"
  threshold          = "0"
  alarm_description  = "Lambda 2 function errors detected"
  alarm_actions      = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.symbol_lookup.function_name
  }

  tags = local.common_tags
}