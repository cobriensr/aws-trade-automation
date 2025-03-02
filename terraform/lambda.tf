# lambda.tf
resource "aws_lambda_function" "main" {
  s3_bucket     = aws_s3_bucket.lambda_deployment.id
  s3_key        = "lambda_function.zip"
  function_name = "${local.name_prefix}-function"
  role          = aws_iam_role.lambda_role.arn
  kms_key_arn   = aws_kms_key.lambda_env.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  timeout       = 15
  memory_size   = 1024
  publish       = true
  layers = [
    "arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:53"
  ]

  environment {
    variables = {
      AWS_LAMBDA_FUNCTION_TIMEOUT       = "30"
      AWS_LAMBDA_INITIALIZATION_TYPE    = "provisioned-concurrency"
      AWS_LAMBDA_INITIALIZATION_TIMEOUT = "25"
      FUNCTION_NAME                     = "${local.name_prefix}-function"
      OANDA_SECRET                      = "${data.aws_ssm_parameter.oanda_secret.value}"
      OANDA_ACCOUNT                     = "${data.aws_ssm_parameter.oanda_account.value}"
      DATABENTO_API_KEY                 = "${data.aws_ssm_parameter.databento_key.value}"
      TRADOVATE_USERNAME                = "${data.aws_ssm_parameter.tradovate_username.value}"
      TRADOVATE_PASSWORD                = "${data.aws_ssm_parameter.tradovate_password.value}"
      TRADOVATE_DEVICE_ID               = "${data.aws_ssm_parameter.tradovate_device_id.value}"
      TRADOVATE_CID                     = "${data.aws_ssm_parameter.tradovate_cid.value}"
      TRADOVATE_SECRET                  = "${data.aws_ssm_parameter.tradovate_secret.value}"
      CACHE_TABLE_NAME                  = aws_dynamodb_table.tradovate_cache.name
    }
  }

  vpc_config {
    subnet_ids         = values(aws_subnet.private)[*].id
    security_group_ids = [aws_security_group.lambda.id, "sg-0f10a7b30f99f2156"]
  }

  tracing_config {
    mode = "Active"
  }

  tags = local.common_tags
}

# Symbol lookup Lambda (now a batch processor)
resource "aws_lambda_function" "symbol_lookup" {
  function_name = "${local.name_prefix}-symbol-lookup"
  kms_key_arn   = aws_kms_key.lambda_env.arn
  role          = aws_iam_role.lambda2_role.arn
  timeout       = 300
  memory_size   = 1024
  package_type  = "Image"
  image_uri     = "565625954376.dkr.ecr.us-east-1.amazonaws.com/trading-prod-symbol-lookup:latest"

  environment {
    variables = {
      FUNCTION_NAME     = "${local.name_prefix}-symbol-lookup"
      DATABENTO_API_KEY = data.aws_ssm_parameter.databento_key.value
      CACHE_TABLE_NAME  = aws_dynamodb_table.tradovate_cache.name
    }
  }

  vpc_config {
    subnet_ids         = values(aws_subnet.private)[*].id
    security_group_ids = [aws_security_group.lambda.id, "sg-0f10a7b30f99f2156"]
  }

  lifecycle {
    ignore_changes = [
      image_uri,
    ]
  }

  tags = local.common_tags
}

# EventBridge rule to trigger the lookup every 12 hours
resource "aws_cloudwatch_event_rule" "symbol_lookup_schedule" {
  name                = "${local.name_prefix}-symbol-lookup-schedule"
  description         = "Triggers symbol lookup Lambda every 12 hours"
  schedule_expression = "rate(12 hours)"
}

resource "aws_cloudwatch_event_target" "symbol_lookup_lambda" {
  rule      = aws_cloudwatch_event_rule.symbol_lookup_schedule.name
  target_id = "SymbolLookupLambda"
  arn       = aws_lambda_function.symbol_lookup.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.symbol_lookup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.symbol_lookup_schedule.arn
}

# Lambda 3 (Coinbase)
resource "aws_lambda_function" "coinbase" {
  s3_bucket     = aws_s3_bucket.lambda_deployment.id
  s3_key        = "lambda3_function.zip"
  function_name = "${local.name_prefix}-coinbase"
  role          = aws_iam_role.lambda2_role.arn
  kms_key_arn   = aws_kms_key.lambda_env.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128
  publish       = true
  layers = [
    "arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:53",
  ]

  environment {
    variables = {
      AWS_LAMBDA_FUNCTION_TIMEOUT       = "30"
      AWS_LAMBDA_INITIALIZATION_TYPE    = "provisioned-concurrency"
      AWS_LAMBDA_INITIALIZATION_TIMEOUT = "25"
      FUNCTION_NAME                     = "${local.name_prefix}-coinbase"
      COINBASE_API_KEY_NAME             = "${data.aws_ssm_parameter.coinbase_api_key_name.value}"
      COINBASE_PRIVATE_KEY              = "${data.aws_ssm_parameter.coinbase_private_key.value}"
    }
  }

  vpc_config {
    subnet_ids         = values(aws_subnet.private)[*].id
    security_group_ids = [aws_security_group.lambda.id, "sg-0f10a7b30f99f2156"]
  }

  tracing_config {
    mode = "Active"
  }

  tags = local.common_tags
}