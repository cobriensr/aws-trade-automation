# lambda.tf
resource "aws_lambda_function" "main" {
  s3_bucket     = aws_s3_bucket.lambda_deployment.id
  s3_key        = "lambda_function.zip"
  function_name = "${local.name_prefix}-function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 1024
  layers = [
    "arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:53",
    "arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:5",
  ]

  environment {
    variables = {
      FUNCTION_NAME           = "${local.name_prefix}-function"
      OANDA_SECRET            = "${data.aws_ssm_parameter.oanda_secret.value}"
      OANDA_ACCOUNT           = "${data.aws_ssm_parameter.oanda_account.value}"
      DATABENTO_API_KEY       = "${data.aws_ssm_parameter.databento_key.value}"
      TRADOVATE_USERNAME      = "${data.aws_ssm_parameter.tradovate_username.value}"
      TRADOVATE_PASSWORD      = "${data.aws_ssm_parameter.tradovate_password.value}"
      TRADOVATE_DEVICE_ID     = "${data.aws_ssm_parameter.tradovate_device_id.value}"
      TRADOVATE_CID           = "${data.aws_ssm_parameter.tradovate_cid.value}"
      TRADOVATE_SECRET        = "${data.aws_ssm_parameter.tradovate_secret.value}"
      LAMBDA2_FUNCTION_NAME   = aws_lambda_function.symbol_lookup.function_name
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-instrument"
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

# Lambda 2 (Symbol lookup)
resource "aws_lambda_function" "symbol_lookup" {
  s3_bucket     = aws_s3_bucket.lambda_deployment.id
  s3_key        = "lambda2_function.zip"
  function_name = "${local.name_prefix}-symbol-lookup"
  role          = aws_iam_role.lambda2_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 1024
  layers = [
    "arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:53",
    "arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:5",
  ]

  environment {
    variables = {
      FUNCTION_NAME           = "${local.name_prefix}-symbol-lookup"
      DATABENTO_API_KEY       = "${data.aws_ssm_parameter.databento_key.value}"
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-instrument"
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

# Lambda 3 (Coinbase)
resource "aws_lambda_function" "coinbase" {
  s3_bucket     = aws_s3_bucket.lambda_deployment.id
  s3_key        = "lambda3_function.zip"
  function_name = "${local.name_prefix}-coinbase"
  role          = aws_iam_role.lambda2_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 1024
  layers = [
    "arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:53",
    "arn:aws:lambda:us-east-1:615299751070:layer:AWSOpenTelemetryDistroPython:5",
  ]

  environment {
    variables = {
      FUNCTION_NAME           = "${local.name_prefix}-coinbase"
      COINBASE_API_KEY_NAME   = "${data.aws_ssm_parameter.coinbase_api_key_name.value}"
      COINBASE_PRIVATE_KEY    = "${data.aws_ssm_parameter.coinbase_private_key.value}"
      AWS_LAMBDA_EXEC_WRAPPER = "/opt/otel-instrument"
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