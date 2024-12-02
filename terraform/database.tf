resource "aws_rds_cluster" "trading_db" {
  cluster_identifier           = "trade-automation"
  engine                      = "aurora-postgresql"
  engine_version              = "16.4"
  database_name               = "tradeAutomation"
  master_username             = "postgres"
  deletion_protection         = true
  backup_retention_period     = 7
  preferred_backup_window     = "05:24-05:54"
  preferred_maintenance_window = "sun:04:25-sun:04:55"
  db_subnet_group_name        = "default-vpc-027bf578d09033c51"
  vpc_security_group_ids      = ["sg-0bdcf8219c98a6ff5", "sg-0b9d4372c88cfef16"]
  storage_encrypted           = true
  enabled_cloudwatch_logs_exports = ["postgresql"]
  copy_tags_to_snapshot = true
  enable_http_endpoint = true
  skip_final_snapshot = true
  serverlessv2_scaling_configuration {
    min_capacity = 8
    max_capacity = 64
  }
  performance_insights_enabled = true
  performance_insights_retention_period = 7

}

resource "aws_rds_cluster_instance" "trading_db_instances" {
  count                = 2
  identifier           = count.index == 0 ? "trade-automation-instance-1" : "trade-automation-instance-1-us-east-1b"
  cluster_identifier   = aws_rds_cluster.trading_db.id
  instance_class      = "db.serverless"
  engine              = aws_rds_cluster.trading_db.engine
  engine_version      = aws_rds_cluster.trading_db.engine_version
  promotion_tier      = 1
  monitoring_interval         = 60
  monitoring_role_arn        = "arn:aws:iam::565625954376:role/rds-monitoring-role"
}