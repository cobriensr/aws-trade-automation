# Create ECR repository for Lambda 2
resource "aws_ecr_repository" "lambda2" {
  name                 = "${local.name_prefix}-symbol-lookup"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# Add lifecycle policy to clean up untagged images
resource "aws_ecr_lifecycle_policy" "lambda2" {
  repository = aws_ecr_repository.lambda2.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 5 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 5
      }
      action = {
        type = "expire"
      }
    }]
  })
}