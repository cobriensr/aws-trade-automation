resource "aws_cloudtrail" "main" {
  name                          = "trading-prod-events"
  enable_log_file_validation    = true
  enable_logging                = true
  include_global_service_events = true
  is_multi_region_trail         = true
  s3_bucket_name                = "aws-cloudtrail-logs-565625954376-0dc47724"
  cloud_watch_logs_group_arn    = "arn:aws:logs:us-east-1:565625954376:log-group:aws-cloudtrail-logs-565625954376-7f92262f:*"
  cloud_watch_logs_role_arn     = "arn:aws:iam::565625954376:role/service-role/AWSCloudTrailLogStream"

  event_selector {
    include_management_events = true
    read_write_type           = "All"

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3"]
    }

    data_resource {
      type   = "AWS::DynamoDB::Table"
      values = ["arn:aws:dynamodb"]
    }
  }

  insight_selector {
    insight_type = "ApiCallRateInsight"
  }

  insight_selector {
    insight_type = "ApiErrorRateInsight"
  }
}

resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "aws-cloudtrail-logs-565625954376-7f92262f"
  log_group_class   = "STANDARD"
  retention_in_days = 0
  skip_destroy      = false
}