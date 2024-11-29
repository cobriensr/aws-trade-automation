# lambda.tf
resource "aws_lambda_function" "main" {
  filename      = "lambda_function.zip"
  function_name = "${local.name_prefix}-function"
  role          = aws_iam_role.lambda_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.9"
  timeout       = 15
  memory_size   = 1024

  environment {
    variables = {
      REDIS_HOST    = aws_elasticache_cluster.main.cache_nodes[0].address
      REDIS_PORT    = aws_elasticache_cluster.main.cache_nodes[0].port
      FUNCTION_NAME = "${local.name_prefix}-function"
    }
  }

  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  tracing_config {
    mode = "Active"
  }

  tags = local.common_tags
}
