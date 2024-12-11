# networking.tf

# Modify VPC resource to add flow logs
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc"
  })
}

# Add VPC Flow Logs
resource "aws_flow_log" "main" {
  iam_role_arn    = aws_iam_role.vpc_flow_logs.arn
  log_destination = aws_cloudwatch_log_group.vpc_flow_logs.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-vpc-flow-logs"
  })
}

# Create multiple public subnets
resource "aws_subnet" "public" {
  for_each = {
    a = "us-east-1a"
    b = "us-east-1b"
  }

  vpc_id                  = aws_vpc.main.id
  cidr_block              = each.key == "a" ? "10.0.0.0/24" : "10.0.3.0/24"
  availability_zone       = each.value
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "trading-${var.environment}-public-subnet-${each.key}"
  })
}

# Create multiple private subnets
resource "aws_subnet" "private" {
  for_each = {
    a = "us-east-1a"
    b = "us-east-1b"
  }

  vpc_id            = aws_vpc.main.id
  cidr_block        = each.key == "a" ? "10.0.1.0/24" : "10.0.2.0/24"
  availability_zone = each.value

  tags = merge(local.common_tags, {
    Name = "trading-${var.environment}-private-subnet-${each.key}"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-igw"
  })
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-nat-eip"
  })
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public["a"].id # Use the first public subnet

  tags = merge(local.common_tags, {
    Name = "trading-${var.environment}-nat"
  })
}

# VPC Endpoint for DynamoDB
resource "aws_vpc_endpoint" "dynamodb" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  # Add directly to the route table
  route_table_ids = [aws_route_table.private.id]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-dynamodb-endpoint"
  })
}