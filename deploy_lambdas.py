"""Deploy Docker-based Lambda functions to AWS."""

import subprocess
import sys
import datetime
import os
import shutil


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


def get_lambda_package_type(function_name):
    """Get the package type (Image or Zip) for a Lambda function."""
    cmd = f"aws lambda get-function --function-name {function_name} --query 'Configuration.PackageType' --output text"
    return run_command(cmd)


def create_zip_package(source_dir):
    """Create a ZIP deployment package for a Lambda function."""
    print(f"Creating ZIP package for {source_dir}...")

    # Create a temporary directory for the package
    temp_dir = f"{source_dir}_deploy"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

    # Copy Python files
    for file in os.listdir(source_dir):
        if file.endswith(".py"):
            shutil.copy2(os.path.join(source_dir, file), temp_dir)

    # Install dependencies from requirements.txt
    requirements_file = os.path.join(source_dir, "requirements.txt")
    if os.path.exists(requirements_file):
        subprocess.run(
            ["pip", "install", "-r", requirements_file, "--target", temp_dir],
            check=True,
        )

    # Create ZIP file
    zip_file = f"{source_dir}.zip"
    if os.path.exists(zip_file):
        os.remove(zip_file)

    shutil.make_archive(source_dir, "zip", temp_dir)

    # Clean up temporary directory
    shutil.rmtree(temp_dir)

    return f"{source_dir}.zip"


def deploy_zip_lambda(source_dir, function_name):
    """Deploy a ZIP-based Lambda function."""
    print(f"\nDeploying ZIP package for {function_name}...")

    try:
        # Create ZIP package
        zip_file = create_zip_package(source_dir)

        # Update Lambda function
        print(f"Updating Lambda function {function_name}...")
        update_cmd = f"aws lambda update-function-code --function-name {function_name} --zip-file fileb://{zip_file}"
        run_command(update_cmd)

        # Clean up ZIP file
        if os.path.exists(zip_file):
            os.remove(zip_file)

        print(f"Successfully deployed {function_name}")
        return True

    except Exception as e:
        print(f"Error deploying {function_name}: {str(e)}")
        return False


def get_ecr_repository_uri(repository_name):
    """Get the ECR repository URI."""
    cmd = f"aws ecr describe-repositories --repository-names {repository_name} --query 'repositories[0].repositoryUri' --output text"
    try:
        return run_command(cmd)
    except subprocess.CalledProcessError:
        print(f"Repository {repository_name} not found. Creating it...")
        try:
            create_cmd = f"aws ecr create-repository --repository-name {repository_name} --query 'repository.repositoryUri' --output text"
            uri = run_command(create_cmd)
            print(f"Successfully created repository: {uri}")
            return uri
        except subprocess.CalledProcessError as e:
            print(f"Failed to create repository: {e.stderr}")
            return None


def deploy_container_lambda(source_dir, repository_name, function_name):
    """Deploy a container-based Lambda function."""
    print(f"\nDeploying container for {function_name}...")

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
    aws_region = "us-east-1"
    aws_account = run_command(
        "aws sts get-caller-identity --query Account --output text"
    )
    ecr_login_cmd = f"aws ecr get-login-password --region {aws_region} | docker login --username AWS --password-stdin {aws_account}.dkr.ecr.{aws_region}.amazonaws.com"
    run_command(ecr_login_cmd)

    # Build Docker image
    print(f"Building Docker image for {source_dir}...")
    build_cmd = f"docker build -t {repository_name}:latest {source_dir}"
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

    print(f"Successfully deployed {function_name}")
    return True


def main():
    # Configure all Lambda functions
    lambdas = [
        ("src/lambda", "trading-prod-function", "trading-prod-function"),
        ("src/lambda2", "trading-prod-symbol-lookup", "trading-prod-symbol-lookup"),
        ("src/lambda3", "trading-prod-coinbase", "trading-prod-coinbase"),
    ]

    for source_dir, repo_name, function_name in lambdas:
        # Get the package type for the function
        package_type = get_lambda_package_type(function_name)

        if package_type == "Image":
            success = deploy_container_lambda(source_dir, repo_name, function_name)
        else:  # 'Zip' package type
            success = deploy_zip_lambda(source_dir, function_name)

        if not success:
            print(f"Failed to deploy {function_name}")
            sys.exit(1)

    print("\nAll Lambda functions deployed successfully!")


if __name__ == "__main__":
    main()
