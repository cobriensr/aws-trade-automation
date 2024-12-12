resource "aws_cloudwatch_dashboard" "trading_metrics" {
  dashboard_name = "TradingWebhookMetrics"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", aws_lambda_function.main.function_name],
            [".", "Duration", ".", "."],
            [".", "Errors", ".", "."],
            [".", "Throttles", ".", "."]
          ]
          period  = 60
          stat    = "Maximum"
          region  = "us-east-1"
          title   = "Trading Function Metrics"
          view    = "timeSeries"
          stacked = false
        }
        width  = 12
        height = 6
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Trading/Webhook", "request_duration", "FunctionName", aws_lambda_function.main.function_name],
            [".", "error_count", ".", "."],
            [".", "client_error_count", ".", "."]
          ]
          period  = 60
          stat    = "Sum"
          region  = "us-east-1"
          title   = "Trading Webhook Custom Metrics"
          view    = "timeSeries"
          stacked = false
        }
        width  = 12
        height = 6
      }
    ]
  })
}

# Add alarms for critical thresholds
resource "aws_cloudwatch_metric_alarm" "concurrent_executions_high" {
  alarm_name          = "trading-function-high-concurrency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Maximum"
  threshold           = 8 # Alert when close to max concurrency
  alarm_description   = "This metric monitors lambda concurrent executions"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "error_rate_high" {
  alarm_name          = "trading-function-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 5 # 5 errors in 5 minutes
  alarm_description   = "This metric monitors lambda error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.main.function_name
  }
}

# Add an email subscription to the SNS topic
resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "jerseyse410@gmail.com"
}

resource "aws_cloudwatch_dashboard" "concurrency_monitoring" {
  dashboard_name = "${local.name_prefix}-concurrency"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["Trading/Webhook/Resources", "MemoryUsedMB"],
            [".", "MemoryPercentage"],
            [".", "RemainingTimeMS"]
          ]
          period = 60
          stat   = "Maximum"
          region = "us-east-1"
          title  = "Resource Usage During Concurrent Executions"
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["Trading/Webhook/Execution", "Status_Started"],
            [".", "Status_Completed"],
            [".", "Status_Failed"]
          ]
          period = 60
          stat   = "Sum"
          region = "us-east-1"
          title  = "Execution Status"
        }
      }
    ]
  })
}