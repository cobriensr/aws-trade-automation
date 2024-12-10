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
          "logs:PutLogEvents",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "secretsmanager:GetSecretValue",
          "lambda:InvokeFunction"
        ]
        Resource = "*"
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

# Allow API Gateway to invoke the Lambda function and write logs
resource "aws_iam_role_policy" "api_gateway_policy" {
  name = "${local.name_prefix}-api-gateway-policy"
  role = aws_iam_role.api_gateway_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = aws_lambda_function.main.arn
      },
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

# Lambda 2 policy
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
          "logs:PutLogEvents",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface",
          "lambda:InvokeFunction"
        ]
        Resource = "*"
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

# Lambda 3 policy
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
          "logs:PutLogEvents",
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
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

# Add CloudWatch metrics permission to lambda policy
resource "aws_iam_role_policy" "lambda_cloudwatch" {
  name = "cloudwatch_metrics_access"
  role = aws_iam_role.lambda_role.id

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

# Add ECR permissions to Lambda 2 role
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
        Resource = aws_ecr_repository.lambda2.arn
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

# Create IAM role policy for VPC Flow Logs
resource "aws_iam_role_policy" "vpc_flow_logs" {
  name = "${local.name_prefix}-vpc-flow-logs"
  role = aws_iam_role.vpc_flow_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams"
        ]
        Effect   = "Allow"
        Resource = "${aws_cloudwatch_log_group.vpc_flow_logs.arn}:*"
      }
    ]
  })
}

# Add KMS permissions to lambda_policy for the main Lambda role
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
        Resource = aws_kms_key.rds.arn
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

# Add S3 and KMS permissions for Lambda roles to access encrypted buckets
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
          aws_kms_key.rds.arn
        ]
      }
    ]
  })
}