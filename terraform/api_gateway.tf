#api_gateway.tf

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins  = ["*"]
    allow_methods  = ["POST", "GET", "OPTIONS"]
    allow_headers  = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"]
    expose_headers = ["Content-Type"]
    max_age        = 300
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_stage" "main" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit   = 100
    throttling_rate_limit    = 50
    detailed_metrics_enabled = true
    logging_level            = "INFO"
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

# Single integration for all routes
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.main.invoke_arn
  payload_format_version = "2.0"
  description            = "Lambda integration for all endpoints"
}

# Routes using the single integration
resource "aws_apigatewayv2_route" "healthcheck" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /healthcheck"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "oandastatus" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /oandastatus"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "tradovateaccounts" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /tradovateaccounts"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "tradovatestatus" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /tradovatestatus"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /webhook"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}