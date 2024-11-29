
# api_gateway.tf
resource "aws_apigatewayv2_api" "main" {
  name            = "${local.name_prefix}-api"
  protocol_type   = "HTTP"
  credentials_arn = aws_iam_role.api_gateway_role.arn
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST"]
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
    })
  }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.main.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "main" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# Healthcheck endpoint configuration
resource "aws_apigatewayv2_route" "healthcheck" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /healthcheck"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_integration" "healthcheck" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.main.invoke_arn
  payload_format_version = "2.0"
}

# Oandastatus endpoint configuration
resource "aws_apigatewayv2_route" "oandastatus" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /oandastatus"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_integration" "oandastatus" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.main.invoke_arn
  payload_format_version = "2.0"
}