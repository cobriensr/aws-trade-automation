FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .
COPY trading/ trading/

# Install packages to a temporary directory, clean them up, and copy to function directory
RUN pip install --target . --no-cache-dir -r requirements.txt && \
    # Remove all test/example/doc directories
    find . -type d -name "tests" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "test" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "*test*" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "examples" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "docs" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "doc" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "*docs*" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "documentation" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "locale" -not -path "*/botocore/*" -exec rm -rf {} + && \
    find . -type d -name "locales" -not -path "*/botocore/*" -exec rm -rf {} + && \
    # Remove development files
    find . -name "*.c" -not -path "*/botocore/*" -delete && \
    find . -name "*.h" -not -path "*/botocore/*" -delete && \
    find . -name "*.pxd" -not -path "*/botocore/*" -delete && \
    find . -name "*.pyx" -not -path "*/botocore/*" -delete && \
    find . -name "*.so.*" -not -path "*/botocore/*" -delete && \
    find . -name "*.pyi" -not -path "*/botocore/*" -delete && \
    find . -name "*.pyc" -not -path "*/botocore/*" -delete && \
    find . -name "*.pyo" -not -path "*/botocore/*" -delete && \
    find . -name "*.egg-info" -not -path "*/botocore/*" -exec rm -rf {} + && \
    # Remove documentation files
    find . -name "README*" -not -path "*/botocore/*" -delete && \
    find . -name "readme*" -not -path "*/botocore/*" -delete && \
    find . -name "CHANGELOG*" -not -path "*/botocore/*" -delete && \
    find . -name "AUTHORS*" -not -path "*/botocore/*" -delete && \
    find . -name "CONTRIBUTING*" -not -path "*/botocore/*" -delete && \
    find . -name "LICENSE*" -not -path "*/botocore/*" -delete && \
    find . -name "*.md" -not -path "*/botocore/*" -delete && \
    find . -name "*.rst" -not -path "*/botocore/*" -delete && \
    # Remove cache and build artifacts
    find . -name "__pycache__" -not -path "*/botocore/*" -exec rm -rf {} + && \
    # Remove data files
    find . -name "*.csv" -not -path "*/botocore/*" -delete && \
    find . -name "*.json" -not -path "*/botocore/*" -delete && \
    find . -name "*.yaml" -not -path "*/botocore/*" -delete && \
    find . -name "*.xml" -not -path "*/botocore/*" -delete && \
    find . -name "*.ipynb" -not -path "*/botocore/*" -delete && \
    find . -name "sample*" -not -path "*/botocore/*" -delete && \
    find . -name "example*" -not -path "*/botocore/*" -delete && \
    find . -name "dataset*" -not -path "*/botocore/*" -delete && \
    find . -name "*.pkl" -not -path "*/botocore/*" -delete

# Create deployment package
RUN zip -r /lambda_function.zip .

CMD ["main.lambda_handler"]