# security.tf

resource "aws_security_group" "lambda" {
  name        = "${local.name_prefix}-lambda-sg"
  description = "Security group for Lambda function"
  vpc_id      = aws_vpc.main.id

  # Allow HTTPS outbound for API calls to trading services
  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS outbound traffic for Databento, Tradovate, Oanda, and Coinbase APIs"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-lambda-sg"
  })
}

# Add a security group rule to allow HTTPS inbound for the VPC endpoints
resource "aws_security_group_rule" "lambda_to_vpce" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.lambda.id
  source_security_group_id = aws_security_group.lambda.id
  description              = "Allow HTTPS inbound from Lambda functions to VPC endpoints"
}