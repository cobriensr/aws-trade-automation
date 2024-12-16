# iam.tf

# Create an IAM role for the Lambda function
resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda_error_handling" {
  name = "${local.name_prefix}-error-handling"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:GetFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:ListTags",
          "lambda:ListVersionsByFunction"
        ]
        Resource = [
          aws_lambda_function.symbol_lookup.arn,
          aws_lambda_function.coinbase.arn,
          aws_lambda_function.main.arn
        ]
      }
    ]
  })
}

# Allow the Lambda function to write logs to CloudWatch, create and delete network interfaces, and retrieve secrets from Secrets Manager
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.name_prefix}-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.main.function_name}",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.main.function_name}:log-stream:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
        ]
        Condition = {
          StringEquals = {
            "ec2:Subnet" : [
              aws_subnet.private["a"].id,
              aws_subnet.private["b"].id
            ],
            "ec2:vpc" : aws_vpc.main.id
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
        ]
      }
    ]
  })
}

# Attach the AWSXRayDaemonWriteAccess policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Allow the Lambda function to read and write parameters in Parameter Store
resource "aws_iam_role_policy" "lambda_parameter_store" {
  name = "parameter_store_access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/tradovate/*"
      }
    ]
  })
}

# Create an IAM role for API Gateway
resource "aws_iam_role" "api_gateway_role" {
  name = "${local.name_prefix}-api-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# API Gateway policy
resource "aws_iam_role_policy" "api_gateway_policy" {
  name = "${local.name_prefix}-api-gateway-policy"
  role = aws_iam_role.api_gateway_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.main.arn,
          aws_lambda_function.coinbase.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.api_logs.arn}",
          "${aws_cloudwatch_log_group.api_logs.arn}:log-stream:*"
        ]
      }
    ]
  })
}

# Create an IAM role for Lambda 2
resource "aws_iam_role" "lambda2_role" {
  name = "${local.name_prefix}-lambda2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Lambda 2 (Symbol Lookup) policy
resource "aws_iam_role_policy" "lambda2_policy" {
  name = "${local.name_prefix}-lambda2-policy"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.symbol_lookup.function_name}",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.symbol_lookup.function_name}:log-stream:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
        ]
        Condition = {
          StringEquals = {
            "ec2:Subnet" : [
              aws_subnet.private["a"].id,
              aws_subnet.private["b"].id
            ],
            "ec2:vpc" : aws_vpc.main.id
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
        ]
      }
    ]
  })
}

# Attach CloudWatch metrics policy to Lambda 2 
resource "aws_iam_role_policy" "lambda2_cloudwatch" {
  name = "cloudwatch_metrics_access"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach CloudWatch metrics policy to Lambda 23
resource "aws_iam_role_policy" "lambda3_cloudwatch" {
  name = "cloudwatch_metrics_access"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach X-Ray policy to Lambda 2
resource "aws_iam_role_policy_attachment" "lambda2_xray" {
  role       = aws_iam_role.lambda2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Allow Lambda 2 to access Databento API key from Parameter Store
resource "aws_iam_role_policy" "lambda2_parameter_store" {
  name = "databento_parameter_access"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/tradovate/*"
      }
    ]
  })
}

# Create an IAM role for Lambda 3
resource "aws_iam_role" "lambda3_role" {
  name = "${local.name_prefix}-lambda3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

# Lambda 3 (Coinbase) policy
resource "aws_iam_role_policy" "lambda3_policy" {
  name = "${local.name_prefix}-lambda3-policy"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.coinbase.function_name}",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${aws_lambda_function.coinbase.function_name}:log-stream:*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
        ]
        Condition = {
          StringEquals = {
            "ec2:Subnet" : [
              aws_subnet.private["a"].id,
              aws_subnet.private["b"].id
            ],
            "ec2:vpc" : aws_vpc.main.id
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:network-interface/*"
        ]
      }
    ]
  })
}

# Attach X-Ray policy to Lambda 3
resource "aws_iam_role_policy_attachment" "lambda3_xray" {
  role       = aws_iam_role.lambda3_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Allow Lambda 3 to access Coinbase API key name from Parameter Store
resource "aws_iam_role_policy" "lambda3_parameter_store" {
  name = "coinbase_parameter_access"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:PutParameter",
          "ssm:GetParameters"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/tradovate/*",
        ]
      }
    ]
  })
}

# Lambda CloudWatch metrics policy
resource "aws_iam_role_policy" "lambda_cloudwatch" {
  name = "cloudwatch_metrics_access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*" # CloudWatch metrics require "*" for resource
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" : [
              "Trading/Webhook",
              "Trading/SymbolLookup",
              "Trading/Webhook/Resources",
              "Trading/Webhook/Execution",
              "Trading/Custom"
            ]
          }
        }
      }
    ]
  })
}

resource "aws_iam_role" "coinbase_api_gateway_role" {
  name = "${local.name_prefix}-coinbase-api-gateway-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "coinbase_api_gateway_policy" {
  name = "${local.name_prefix}-coinbase-api-gateway-policy"
  role = aws_iam_role.coinbase_api_gateway_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.coinbase.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ]
        Resource = [
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/*",
          "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/apigateway/*:log-stream:*",
          "${aws_cloudwatch_log_group.api_logs.arn}",
          "${aws_cloudwatch_log_group.api_logs.arn}:*"
        ]
      }
    ]
  })
}

# Lambda 2 ECR access policy
resource "aws_iam_role_policy" "lambda2_ecr" {
  name = "${local.name_prefix}-lambda2-ecr"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = [aws_ecr_repository.lambda2.arn]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda2_insights" {
  role       = aws_iam_role.lambda2_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"
}

# Create IAM role for VPC Flow Logs
resource "aws_iam_role" "vpc_flow_logs" {
  name = "${local.name_prefix}-vpc-flow-logs"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

# VPC Flow Logs policy
resource "aws_iam_role_policy" "vpc_flow_logs" {
  name = "${local.name_prefix}-vpc-flow-logs"
  role = aws_iam_role.vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${aws_cloudwatch_log_group.vpc_flow_logs.arn}",
          "${aws_cloudwatch_log_group.vpc_flow_logs.arn}:log-stream:${data.aws_caller_identity.current.account_id}_vpcflowlogs_${var.aws_region}_${aws_vpc.main.id}"
        ]
      }
    ]
  })
}


# KMS key policies
resource "aws_iam_role_policy" "lambda_kms" {
  name = "${local.name_prefix}-lambda-kms"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          aws_kms_key.rds.arn,
          aws_kms_key.s3.arn,
          aws_kms_key.cloudwatch_logs.arn,
          aws_kms_key.lambda_env.arn
        ]
      }
    ]
  })
}

# Add KMS permissions for Lambda2 role
resource "aws_iam_role_policy" "lambda2_kms" {
  name = "${local.name_prefix}-lambda2-kms"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.rds.arn
      }
    ]
  })
}

# Add KMS permissions for Lambda3 role
resource "aws_iam_role_policy" "lambda3_kms" {
  name = "${local.name_prefix}-lambda3-kms"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.rds.arn
      }
    ]
  })
}

# Add Secrets Manager permissions to lambda roles
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${local.name_prefix}-secrets"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.rds_password.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda2_secrets" {
  name = "${local.name_prefix}-secrets"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.rds_password.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda3_secrets" {
  name = "${local.name_prefix}-secrets"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.rds_password.arn
      }
    ]
  })
}

# S3 bucket access policies
resource "aws_iam_role_policy" "lambda_s3" {
  name = "${local.name_prefix}-lambda-s3"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "${aws_s3_bucket.lambda_deployment.arn}/*",
          "${aws_s3_bucket.access_logs.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.lambda_deployment.arn,
          aws_s3_bucket.access_logs.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda2_s3" {
  name = "${local.name_prefix}-lambda2-s3"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.lambda_deployment.arn,
          "${aws_s3_bucket.lambda_deployment.arn}/*",
          aws_s3_bucket.access_logs.arn,
          "${aws_s3_bucket.access_logs.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.s3.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda3_s3" {
  name = "${local.name_prefix}-lambda3-s3"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.lambda_deployment.arn,
          "${aws_s3_bucket.lambda_deployment.arn}/*",
          aws_s3_bucket.access_logs.arn,
          "${aws_s3_bucket.access_logs.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.s3.arn
      }
    ]
  })
}

# Add KMS permissions for GitHub Actions (admin user)
resource "aws_iam_user_policy" "admin_kms" {
  name = "${local.name_prefix}-admin-kms"
  user = "admin"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:CreateGrant",
          "kms:ListGrants",
          "kms:RevokeGrant",
          "kms:Encrypt",
          "kms:DescribeKey"
        ]
        Resource = [
          aws_kms_key.s3.arn,
          aws_kms_key.rds.arn,
          aws_kms_key.ecr.arn,
          aws_kms_key.cloudwatch_logs.arn,
          aws_kms_key.cloudtrail.arn
        ]
      }
    ]
  })
}

# Add DynamoDB permissions to lambda_policy
# DynamoDB access policy
resource "aws_iam_role_policy" "lambda_dynamodb" {
  name = "${local.name_prefix}-dynamodb"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:DescribeTable"
        ]
        Resource = [
          aws_dynamodb_table.tradovate_tokens.arn,
          aws_dynamodb_table.tradovate_cache.arn
        ]
      }
    ]
  })
}


resource "aws_iam_role" "cloudtrail_cloudwatch" {
  name                  = "AWSCloudTrailLogStream"
  path                  = "/service-role/"
  description           = "Role for config CloudWathLogs for trail trading-prod-events"
  force_detach_policies = false
  max_session_duration  = 3600

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
      }
    ]
  })
}

# CloudTrail CloudWatch policy
resource "aws_iam_policy" "cloudtrail_cloudwatch" {
  name = "Cloudtrail-CW-access-policy-trading-prod-events"
  path = "/service-role/"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["logs:CreateLogStream"]
        Resource = [
          "${aws_cloudwatch_log_group.cloudtrail.arn}:log-stream:${data.aws_caller_identity.current.account_id}_CloudTrail_${var.aws_region}*"
        ]
      },
      {
        Effect = "Allow"
        Action = ["logs:PutLogEvents"]
        Resource = [
          "${aws_cloudwatch_log_group.cloudtrail.arn}:log-stream:${data.aws_caller_identity.current.account_id}_CloudTrail_${var.aws_region}*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "cloudtrail_cloudwatch" {
  role       = aws_iam_role.cloudtrail_cloudwatch.name
  policy_arn = aws_iam_policy.cloudtrail_cloudwatch.arn
}

# Add KMS permissions for CloudWatch Logs to Lambda roles
resource "aws_iam_role_policy" "lambda_cloudwatch_kms" {
  name = "${local.name_prefix}-lambda-cloudwatch-kms"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda2_cloudwatch_kms" {
  name = "${local.name_prefix}-lambda2-cloudwatch-kms"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda3_cloudwatch_kms" {
  name = "${local.name_prefix}-lambda3-cloudwatch-kms"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

# Add KMS permissions for API Gateway roles
resource "aws_iam_role_policy" "api_gateway_cloudwatch_kms" {
  name = "${local.name_prefix}-api-gateway-cloudwatch-kms"
  role = aws_iam_role.api_gateway_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "coinbase_api_gateway_cloudwatch_kms" {
  name = "${local.name_prefix}-coinbase-api-gateway-cloudwatch-kms"
  role = aws_iam_role.coinbase_api_gateway_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

# Add KMS permissions for VPC Flow Logs role
resource "aws_iam_role_policy" "vpc_flow_logs_kms" {
  name = "${local.name_prefix}-vpc-flow-logs-kms"
  role = aws_iam_role.vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

# Add KMS permissions for CloudTrail role
resource "aws_iam_role_policy" "cloudtrail_cloudwatch_kms" {
  name = "${local.name_prefix}-cloudtrail-cloudwatch-kms"
  role = aws_iam_role.cloudtrail_cloudwatch.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.cloudwatch_logs.arn
      }
    ]
  })
}

# KMS key for CloudWatch Log Group encryption
resource "aws_kms_key" "cloudwatch_logs" {
  description             = "KMS key for CloudWatch Logs encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCloudWatchLogs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${data.aws_region.current.name}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt*",
          "kms:Decrypt*",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "cloudwatch_logs" {
  name          = "alias/cloudwatch-logs"
  target_key_id = aws_kms_key.cloudwatch_logs.key_id
}

# KMS key for ECR repository encryption
resource "aws_kms_key" "ecr" {
  description             = "KMS key for ECR repository encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowECRService"
        Effect = "Allow"
        Principal = {
          Service = "ecr.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "ecr" {
  name          = "alias/ecr-encryption"
  target_key_id = aws_kms_key.ecr.key_id
}

# KMS key for CloudTrail encryption
resource "aws_kms_key" "cloudtrail" {
  description             = "KMS key for CloudTrail encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudTrail to encrypt logs"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:Decrypt"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.${data.aws_region.current.name}.amazonaws.com"
        }
        Action = [
          "kms:Encrypt*",
          "kms:Decrypt*",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:Describe*"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "cloudtrail" {
  name          = "alias/cloudtrail"
  target_key_id = aws_kms_key.cloudtrail.key_id
}

# Add ECR repository policy
resource "aws_ecr_repository_policy" "lambda2_ecr_policy" {
  repository = aws_ecr_repository.lambda2.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.lambda2_role.arn
        }
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:GetAuthorizationToken"
        ]
      },
      {
        Sid    = "LambdaECRImageRetrievalPolicy"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:SetRepositoryPolicy",
          "ecr:DeleteRepositoryPolicy",
          "ecr:GetRepositoryPolicy"
        ]
        Condition = {
          StringLike = {
            "aws:sourceArn" = "arn:aws:lambda:us-east-1:${data.aws_caller_identity.current.account_id}:function:*"
          }
        }
      }
    ]
  })
}

# KMS key for Lambda environment variables encryption
resource "aws_kms_key" "lambda_env" {
  description             = "KMS key for Lambda environment variables encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow Lambda Service"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_kms_alias" "lambda_env" {
  name          = "alias/lambda-environment"
  target_key_id = aws_kms_key.lambda_env.key_id
}

# Add KMS permissions for Lambda environment variables
resource "aws_iam_role_policy" "lambda_env_kms" {
  name = "${local.name_prefix}-lambda-env-kms"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:ReEncrypt*"
        ]
        Resource = aws_kms_key.lambda_env.arn
      }
    ]
  })
}

# Add KMS permissions for Lambda2 environment variables
resource "aws_iam_role_policy" "lambda2_env_kms" {
  name = "${local.name_prefix}-lambda2-env-kms"
  role = aws_iam_role.lambda2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:ReEncrypt*"
        ]
        Resource = aws_kms_key.lambda_env.arn
      }
    ]
  })
}

# Add KMS permissions for Lambda3 environment variables
resource "aws_iam_role_policy" "lambda3_env_kms" {
  name = "${local.name_prefix}-lambda3-env-kms"
  role = aws_iam_role.lambda3_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:ReEncrypt*"
        ]
        Resource = aws_kms_key.lambda_env.arn
      }
    ]
  })
}