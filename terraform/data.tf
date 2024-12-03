# data.tf

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_security_group" "rds" {
  id = "sg-04fd04b67174f23cf"
}
data "aws_security_group" "lambda" {
  id = "sg-0f10a7b30f99f2156"
}