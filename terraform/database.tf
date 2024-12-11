# Create a secret for RDS master password
resource "aws_secretsmanager_secret" "rds_password" {
  name        = "${local.name_prefix}-rds-master-password"
  description = "Master password for RDS cluster"
  kms_key_id  = aws_kms_key.rds.id # Use the same KMS key we created for RDS

  tags = local.common_tags
}

# Generate and store a random password
resource "random_password" "rds_password" {
  length           = 16
  special          = true
  override_special = "!#$%^&*()-_=+[]{}<>:?"
}

resource "aws_secretsmanager_secret_version" "rds_password" {
  secret_id     = aws_secretsmanager_secret.rds_password.id
  secret_string = random_password.rds_password.result
}

# Create KMS key for RDS encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS cluster encryption"
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
        Sid    = "Allow RDS to use the key"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey",
          "kms:CreateGrant"
        ]
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

# Alias for the key
resource "aws_kms_alias" "rds" {
  name          = "alias/${local.name_prefix}-rds"
  target_key_id = aws_kms_key.rds.key_id
}


# Update the RDS cluster with the password and encryption
resource "aws_rds_cluster" "trading_db" {
  cluster_identifier = "trade-automation"
  engine             = "aurora-postgresql"
  engine_version     = "16.4"
  database_name      = "tradeAutomation"
  master_username    = "postgres"
  master_password    = random_password.rds_password.result # Add the password here

  # Encryption configuration
  storage_encrypted = true
  kms_key_id        = aws_kms_key.rds.arn

  deletion_protection             = false
  backup_retention_period         = 2
  preferred_backup_window         = "05:24-05:54"
  preferred_maintenance_window    = "sun:04:25-sun:04:55"
  db_subnet_group_name            = "default-vpc-027bf578d09033c51"
  vpc_security_group_ids          = ["sg-0bdcf8219c98a6ff5", "sg-0b9d4372c88cfef16", "sg-04fd04b67174f23cf"]
  enabled_cloudwatch_logs_exports = ["postgresql"]
  copy_tags_to_snapshot           = true
  enable_http_endpoint            = false
  skip_final_snapshot             = true

  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2
  }

  performance_insights_enabled = false

  tags = local.common_tags
}

resource "aws_rds_cluster_instance" "trading_db_instances" {
  count              = 1
  identifier         = "trade-automation-instance-1"
  cluster_identifier = aws_rds_cluster.trading_db.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.trading_db.engine
  engine_version     = aws_rds_cluster.trading_db.engine_version
}

# DynamoDB table for Tradovate token management
resource "aws_dynamodb_table" "tradovate_tokens" {
  name         = "${local.name_prefix}-tradovate-tokens"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.rds.arn # Reusing your existing KMS key
  }

  tags = local.common_tags
}

# Add to database.tf
resource "aws_dynamodb_table" "tradovate_cache" {
  name         = "${local.name_prefix}-tradovate-cache"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "cache_key"

  attribute {
    name = "cache_key"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.rds.arn
  }

  tags = local.common_tags
}