resource "aws_cloudwatch_dashboard" "trading" {
  dashboard_name = "${local.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["Trading/Custom", "MessageProcessing", "EventType", "trend_validator"],
            ["Trading/Custom", "MessageProcessing", "EventType", "di_cross"]
          ]
          view   = "timeSeries"
          region = var.aws_region
          title  = "Message Processing Times"
        }
      }
    ]
  })
}