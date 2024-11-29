# lambda.tf
resource "aws_lambda_function" "main" {
  filename         = "lambda_function.zip"
  source_code_hash = filebase64sha256("lambda_function.zip")
  function_name    = "${local.name_prefix}-function"
  role             = aws_iam_role.lambda_role.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 1024

  environment {
    variables = {
      FUNCTION_NAME = "${local.name_prefix}-function"
      OANDA_SECRET  = var.oanda_secret
      OANDA_ACCOUNT = var.oanda_account
    }
  }

  vpc_config {
    subnet_ids         = values(aws_subnet.private)[*].id
    security_group_ids = [aws_security_group.lambda.id]
  }

  tracing_config {
    mode = "Active"
  }

  tags = local.common_tags
}
