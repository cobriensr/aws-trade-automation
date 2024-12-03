resource "aws_s3_bucket" "lambda_deployment" {
  bucket = "trading-lambda-deployment"
}

resource "aws_s3_bucket_versioning" "lambda_deployment" {
  bucket = aws_s3_bucket.lambda_deployment.id
  versioning_configuration {
    status = "Enabled"
  }
}