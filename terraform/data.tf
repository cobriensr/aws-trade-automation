# data.tf

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_security_group" "rds" {
  id = "sg-04fd04b67174f23cf"
}
data "aws_security_group" "lambda" {
  id = "sg-0f10a7b30f99f2156"
}

data "aws_ssm_parameter" "oanda_account" {
  name = "/tradovate/OANDA_ACCOUNT"
}

data "aws_ssm_parameter" "oanda_secret" {
  name = "/tradovate/OANDA_SECRET"
}

data "aws_ssm_parameter" "tradovate_username" {
  name = "/tradovate/USERNAME"
}

data "aws_ssm_parameter" "tradovate_password" {
  name = "/tradovate/PASSWORD"
}

data "aws_ssm_parameter" "tradovate_device_id" {
  name = "/tradovate/DEVICE_ID"
}

data "aws_ssm_parameter" "tradovate_cid" {
  name = "/tradovate/CID"
}

data "aws_ssm_parameter" "tradovate_secret" {
  name = "/tradovate/SECRET"
}

data "aws_ssm_parameter" "databento_key" {
  name = "/tradovate/DATABENTO_API_KEY"
}

data "aws_ssm_parameter" "coinbase_api_key_name" {
  name = "/tradovate/COINBASE_API_KEY_NAME"
}

data "aws_ssm_parameter" "coinbase_private_key" {
  name = "/tradovate/COINBASE_PRIVATE_KEY"
}