"""Deploy Docker-based Lambda functions to AWS."""

import subprocess
import sys
import datetime
import os
import shutil
import base64
import json
import time


class DeploymentError(Exception):
    """Custom exception for deployment-related errors."""


class ECRAuthenticationError(DeploymentError):
    """Exception raised for ECR authentication failures."""


class DockerError(DeploymentError):
    """Exception raised for Docker-related errors."""


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
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}")
        print(f"Error output: {e.stderr}")
        if check:
            sys.exit(1)
        return None


def get_ecr_credentials():
    """Get ECR credentials using AWS CLI with comprehensive error handling."""
    try:
        # Run AWS CLI command to get authorization token
        result = subprocess.run(
            ["aws", "ecr", "get-authorization-token", "--output", "json"],
            capture_output=True,
            text=True,
            check=True,
        )

        # Parse the JSON output
        auth_data = json.loads(result.stdout)

        # Extract the base64 encoded token
        auth_token = auth_data["authorizationData"][0]["authorizationToken"]

        # Decode the token
        decoded = base64.b64decode(auth_token).decode("utf-8")

        # Split into username and password
        username, password = decoded.split(":", 1)

        return username, password

    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        IndexError,
        KeyError,
    ) as e:
        print(f"Authentication error: {e}")
        raise ECRAuthenticationError(f"Failed to get ECR credentials: {e}") from e


def docker_login_ecr(repository_uri):
    """Perform Docker login to ECR with enhanced error handling."""
    try:
        # Get ECR credentials
        username, password = get_ecr_credentials()

        # Construct login command
        login_cmd = [
            "docker",
            "login",
            "-u",
            username,
            "--password-stdin",
            repository_uri,
        ]

        # Execute login
        login_process = subprocess.Popen(
            login_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Pass password via stdin
        stdout, stderr = login_process.communicate(input=password)

        if login_process.returncode != 0:
            print(f"Docker login failed: {stderr}")
            return False

        if "Login Succeeded" in stdout:
            print("Successfully logged into ECR")
            return True

        print(f"Unexpected login output: {stdout}")
        return False

    except Exception as e:
        print(f"ECR login error: {str(e)}")
        return False


def build_docker_image(repository_uri, image_tag):
    """Build Docker image with proper platform handling."""
    try:
        full_tag = f"{repository_uri}:{image_tag}"

        # Clean up any existing images
        print("\nCleaning up any existing images...")
        cleanup_cmd = "docker system prune -f"
        subprocess.run(cleanup_cmd, shell=True, check=False)

        # Build command with platform specification
        build_cmd = [
            "docker",
            "build",
            "--progress=plain",
            "--no-cache",
            "--platform",
            "linux/amd64",  # Platform specified here instead of Dockerfile
            "--build-arg",
            "BUILDKIT_INLINE_CACHE=1",  # Enable inline caching
            "-t",
            full_tag,
            ".",
        ]

        print(f"\nStarting build for: {full_tag}")
        print("This may take several minutes...")
        print(f"Build command: {' '.join(build_cmd)}")

        # Set environment variables for build
        env = os.environ.copy()
        env["DOCKER_BUILDKIT"] = "1"  # Enable BuildKit

        # Run build with environment variables
        build_result = subprocess.run(
            build_cmd, env=env, capture_output=True, text=True, check=True
        )

        print(build_result.stdout)

        if build_result.returncode != 0:
            raise DockerError(f"Build failed: {build_result.stderr}")

        print("\nBuild completed successfully!")
        return True

    except Exception as e:
        print(f"\nBuild failed: {str(e)}")
        return False


def push_docker_image(repository_uri, image_tag):
    """Push Docker image to ECR with manifest handling."""
    try:
        # Build the image first
        if not build_docker_image(repository_uri, image_tag):
            return False

        full_tag = f"{repository_uri}:{image_tag}"
        region = "us-east-1"

        # Get ECR credentials with explicit region
        print("\nGetting ECR credentials...")
        auth_cmd = ["aws", "ecr", "get-login-password", "--region", region]
        auth_token = subprocess.run(
            auth_cmd, capture_output=True, text=True, check=True
        ).stdout.strip()

        # Login to ECR
        print("Logging into ECR...")
        registry = repository_uri.split("/")[0]
        login_cmd = [
            "docker",
            "login",
            "--username",
            "AWS",
            "--password-stdin",
            registry,
        ]

        login_process = subprocess.Popen(
            login_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        _, stderr = login_process.communicate(input=auth_token)

        if login_process.returncode != 0:
            raise DockerError(f"Docker login failed: {stderr}")

        print("Successfully logged into ECR")

        # Ensure proper manifest format
        inspect_cmd = ["docker", "inspect", full_tag]
        subprocess.run(inspect_cmd, capture_output=True, text=True, check=True)

        # Push the image
        print(f"\nPushing image: {full_tag}")
        push_cmd = [
            "docker",
            "push",
            "--platform",
            "linux/amd64",  # Explicitly set platform
            full_tag,
        ]

        # Execute push with retries
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"\nPush attempt {attempt + 1} of {max_retries}")
                subprocess.run(push_cmd, capture_output=True, text=True, check=True)
                print("Push completed successfully!")
                return True

            except subprocess.CalledProcessError as e:
                print(f"Push attempt {attempt + 1} failed:")
                print(f"Error output: {e.stderr}")

                if attempt < max_retries - 1:
                    print("Refreshing ECR credentials and retrying...")
                    # Re-authenticate before retry
                    auth_token = subprocess.run(
                        auth_cmd, capture_output=True, text=True, check=True
                    ).stdout.strip()

                    login_process = subprocess.Popen(
                        login_cmd,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    login_process.communicate(input=auth_token)
                    time.sleep(10)

        print("\nAll push attempts failed")
        return False

    except Exception as e:
        print(f"Error in push_docker_image: {str(e)}")
        return False


def debug_ecr_setup(repository_uri):
    """Debug ECR setup and permissions."""
    try:
        print("\nDebug: Checking ECR setup...")
        region = "us-east-1"
        repo_name = repository_uri.split("/")[-1]

        # Check AWS credentials
        print("\n1. Checking AWS credentials...")
        sts_cmd = ["aws", "sts", "get-caller-identity"]
        sts_result = subprocess.run(sts_cmd, capture_output=True, text=True, check=True)
        print(f"AWS Identity: {sts_result.stdout}")

        # Check ECR repository
        print("\n2. Checking ECR repository...")
        describe_cmd = [
            "aws",
            "ecr",
            "describe-repositories",
            "--repository-names",
            repo_name,
            "--region",
            region,
        ]
        repo_result = subprocess.run(
            describe_cmd, capture_output=True, text=True, check=True
        )
        print(f"Repository info: {repo_result.stdout}")

        # Check ECR authorization token
        print("\n3. Checking ECR authorization...")
        auth_cmd = ["aws", "ecr", "get-authorization-token", "--region", region]
        subprocess.run(auth_cmd, capture_output=True, text=True, check=True)
        print("ECR authorization token retrieved successfully")

        # Check Docker configuration
        print("\n4. Checking Docker configuration...")
        subprocess.run(["docker", "info"], capture_output=True, text=True, check=True)
        print("Docker is running and configured correctly")

        print("\nECR setup appears to be correct.")
        return True

    except subprocess.CalledProcessError as e:
        print("\nError during ECR setup check:")
        print(f"Command: {e.cmd}")
        print(f"Return code: {e.returncode}")
        print(f"Output: {e.stdout}")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"\nUnexpected error during ECR setup check: {str(e)}")
        return False


def get_lambda_package_type(function_name):
    """Get the package type (Image or Zip) for a Lambda function."""
    # Hardcode the package types based on what we know
    package_types = {
        "trading-prod-function": "Zip",
        "trading-prod-symbol-lookup": "Image",
        "trading-prod-coinbase": "Zip",
    }
    return package_types.get(function_name, "Zip")


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

    except (subprocess.CalledProcessError, OSError) as e:
        print(f"Error deploying {function_name}: {str(e)}")
        # Attempt to clean up ZIP file even on error
        try:
            if os.path.exists(zip_file):
                os.remove(zip_file)
        except OSError:
            # Ignore cleanup errors
            pass
        return False


def get_ecr_repository_uri(repository_name):
    """Get the ECR repository URI."""
    account_id = run_command(
        "aws sts get-caller-identity --query Account --output text"
    )
    region = "us-east-1"  # Hardcoded based on your configuration
    return f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}"


def deploy_container_lambda(source_dir, repository_name, function_name):
    """Deploy a container-based Lambda function."""
    print(f"\nDeploying container for {function_name}...")

    try:
        # Get AWS account and repository URI
        aws_account = run_command(
            "aws sts get-caller-identity --query Account --output text"
        )
        if not aws_account:
            raise DeploymentError("Failed to get AWS account ID")

        repository_uri = (
            f"{aws_account}.dkr.ecr.us-east-1.amazonaws.com/{repository_name}"
        )

        # Generate tag
        tag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        image_uri = f"{repository_uri}:{tag}"
        local_tag = f"{repository_name}:latest"

        # Build the image locally first
        print(f"Building Docker image for {source_dir}...")
        try:
            build_cmd = f"docker build -t {local_tag} {source_dir}"
            run_command(build_cmd)
        except subprocess.CalledProcessError as e:
            raise DockerError(f"Failed to build Docker image: {str(e)}") from e

        # Get ECR credentials and login
        print("Authenticating with ECR...")
        try:
            if not docker_login_ecr(repository_uri):
                raise ECRAuthenticationError("Failed to log in to ECR")
        except Exception as e:
            raise ECRAuthenticationError(f"ECR authentication failed: {str(e)}") from e

        # Tag for ECR
        print(f"Tagging image as {image_uri}...")
        try:
            tag_cmd = f"docker tag {local_tag} {image_uri}"
            run_command(tag_cmd)
        except subprocess.CalledProcessError as e:
            raise DockerError(f"Failed to tag image: {str(e)}") from e

        # Push to ECR
        print("Pushing to ECR...")
        if not push_docker_image(repository_uri, tag):
            raise DockerError("Failed to push image to ECR")

        # Update Lambda function
        print("Updating Lambda function...")
        try:
            update_cmd = f"aws lambda update-function-code --function-name {function_name} --image-uri {image_uri}"
            run_command(update_cmd)
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Failed to update Lambda function: {str(e)}") from e

        print(f"Successfully deployed {function_name}")
        return True

    except Exception as e:
        print(f"Error deploying {function_name}: {str(e)}")
        # Clean up any leftover images
        try:
            run_command(f"docker rmi {local_tag} {image_uri}", check=False)
        except subprocess.CalledProcessError:
            print("Failed to clean up Docker images")
        return False


def main():
    try:
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
                # Generate image tag
                image_tag = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                repository_uri = (
                    f"565625954376.dkr.ecr.us-east-1.amazonaws.com/{repo_name}"
                )

                # Add debug check
                if not debug_ecr_setup(repository_uri):
                    print(f"ECR setup check failed for {function_name}")
                    sys.exit(1)

                print(f"\nProcessing container Lambda: {function_name}")
                print(f"Source directory: {source_dir}")
                print(f"Repository URI: {repository_uri}")
                print(f"Image tag: {image_tag}")

                # Change to the correct directory
                original_dir = os.getcwd()
                os.chdir(source_dir)

                try:
                    # Verify directory contents
                    print("\nVerifying directory contents:")
                    print(f"Current directory: {os.getcwd()}")
                    print("Files in directory:")
                    subprocess.run(["dir"], shell=True, check=True)

                    # Build and push image
                    if not push_docker_image(repository_uri, image_tag):
                        print(f"Failed to push image for {function_name}")
                        sys.exit(1)

                    # Update Lambda function
                    print(f"\nUpdating Lambda function {function_name}...")
                    update_cmd = f"aws lambda update-function-code --function-name {function_name} --image-uri {repository_uri}:{image_tag}"
                    result = subprocess.run(
                        update_cmd, capture_output=True, text=True, check=True
                    )
                    print(f"Lambda update result: {result.stdout}")

                finally:
                    # Always return to original directory
                    os.chdir(original_dir)

            else:  # 'Zip' package type
                success = deploy_zip_lambda(source_dir, function_name)
                if not success:
                    print(f"Failed to deploy {function_name}")
                    sys.exit(1)

        print("\nAll Lambda functions deployed successfully!")

    except Exception as e:
        print(f"Deployment failed with error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
