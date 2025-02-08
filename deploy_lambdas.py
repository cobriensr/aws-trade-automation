"""Lambda deployment script using Docker and ECR."""

import subprocess
import sys
import datetime


def run_command(command, check=True):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            check=check,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None


def get_ecr_repository_uri(repository_name):
    """Get the ECR repository URI."""
    cmd = f"aws ecr describe-repositories --repository-names {repository_name} --query 'repositories[0].repositoryUri' --output text"
    try:
        return run_command(cmd)
    except subprocess.CalledProcessError:
        print(f"Creating ECR repository {repository_name}...")
        create_cmd = f"aws ecr create-repository --repository-name {repository_name} --query 'repository.repositoryUri' --output text"
        return run_command(create_cmd)


def deploy_lambda(lambda_dir, repository_name, function_name):
    """Deploy a Docker-based Lambda function."""
    print(f"\nDeploying {lambda_dir}...")

    # Get ECR repository URI
    repository_uri = get_ecr_repository_uri(repository_name)
    if not repository_uri:
        print(f"Failed to get/create ECR repository for {repository_name}")
        return False

    # Generate tag based on timestamp
    tag = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    image_uri = f"{repository_uri}:{tag}"

    # Log into ECR
    print("Logging into ECR...")
    aws_region = run_command("aws configure get region")
    aws_account = run_command(
        "aws sts get-caller-identity --query Account --output text"
    )
    ecr_login_cmd = f"aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin {aws_account}.dkr.ecr.{aws_region}.amazonaws.com"
    run_command(ecr_login_cmd)

    # Build Docker image
    print(f"Building Docker image for {lambda_dir}...")
    build_cmd = f"docker build -t {repository_name}:latest {lambda_dir}"
    run_command(build_cmd)

    # Tag image
    tag_cmd = f"docker tag {repository_name}:latest {image_uri}"
    run_command(tag_cmd)

    # Push to ECR
    print("Pushing to ECR...")
    push_cmd = f"docker push {image_uri}"
    run_command(push_cmd)

    # Update Lambda function
    print("Updating Lambda function...")
    update_cmd = f"aws lambda update-function-code --function-name {function_name} --image-uri {image_uri}"
    run_command(update_cmd)

    print(f"Successfully deployed {lambda_dir}")
    return True


def main():
    # List of Lambda directories, repository names, and function names
    lambdas = [
        ("lambda", "lambda1-repo", "your-lambda-function-name-1"),
        ("lambda2", "lambda2-repo", "your-lambda-function-name-2"),
        ("lambda3", "lambda3-repo", "your-lambda-function-name-3"),
    ]

    for lambda_dir, repo_name, function_name in lambdas:
        success = deploy_lambda(lambda_dir, repo_name, function_name)
        if not success:
            print(f"Failed to deploy {lambda_dir}")
            sys.exit(1)

    print("\nAll Lambda functions deployed successfully!")


if __name__ == "__main__":
    main()
