FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .

# Install packages to a temporary directory, clean them up, and copy to function directory
RUN pip install --target . --no-cache-dir -r requirements.txt && \
    # Remove all test/example/doc directories
    find . -type d -name "tests" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "test" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "*test*" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "examples"-not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "docs" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "doc" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "*docs*" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "documentation" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "locale" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "locales" -not -path "*/botocore/*" -exec rm -rf {} + && \
    # Remove development files
    find . -name "*.c" -delete && \
    find . -name "*.h" -delete && \
    find . -name "*.pxd" -delete && \
    find . -name "*.pyx" -delete && \
    find . -name "*.so.*" -delete && \
    find . -name "*.pyi" -delete && \
    find . -name "*.pyc" -delete && \
    find . -name "*.pyo" -delete && \
    find . -name "*.egg-info" -exec rm -rf {} + && \
    # Remove documentation files
    find . -name "README*" -delete && \
    find . -name "readme*" -delete && \
    find . -name "CHANGELOG*" -delete && \
    find . -name "AUTHORS*" -delete && \
    find . -name "CONTRIBUTING*" -delete && \
    find . -name "LICENSE*" -delete && \
    find . -name "*.md" -delete && \
    find . -name "*.rst" -delete && \
    # Remove cache and build artifacts
    find . -name "__pycache__" -exec rm -rf {} + && \
    # Remove data files
    find . -name "*.csv" -delete && \
    find . -name "*.json" -delete && \
    find . -name "*.yaml" -delete && \
    find . -name "*.xml" -delete && \
    find . -name "*.ipynb" -delete && \
    find . -name "sample*" -delete && \
    find . -name "example*" -delete && \
    find . -name "dataset*" -delete && \
    find . -name "*.pkl" -delete

# Create deployment package
RUN zip -r /lambda3_function.zip .

CMD ["main.lambda_handler"]