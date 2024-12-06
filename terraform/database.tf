resource "aws_rds_cluster" "trading_db" {
  cluster_identifier              = "trade-automation"
  engine                          = "aurora-postgresql"
  engine_version                  = "16.4"
  database_name                   = "tradeAutomation"
  master_username                 = "postgres"
  deletion_protection             = false
  backup_retention_period         = 2
  preferred_backup_window         = "05:24-05:54"
  preferred_maintenance_window    = "sun:04:25-sun:04:55"
  db_subnet_group_name            = "default-vpc-027bf578d09033c51"
  vpc_security_group_ids          = ["sg-0bdcf8219c98a6ff5", "sg-0b9d4372c88cfef16", "sg-04fd04b67174f23cf"]
  storage_encrypted               = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  copy_tags_to_snapshot           = true
  enable_http_endpoint            = false
  skip_final_snapshot            = true
  serverlessv2_scaling_configuration {
    min_capacity = 0.5
    max_capacity = 2
  }
  performance_insights_enabled    = false
}

resource "aws_rds_cluster_instance" "trading_db_instances" {
  count              = 1
  identifier         = "trade-automation-instance-1"
  cluster_identifier = aws_rds_cluster.trading_db.id
  instance_class     = "db.serverless"
  engine             = aws_rds_cluster.trading_db.engine
  engine_version     = aws_rds_cluster.trading_db.engine_version
}