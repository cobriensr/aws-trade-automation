FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Switch to root for system installations and setup
USER root
WORKDIR /function

# Install required tools and setup user in a single layer
RUN microdnf install -y zip findutils shadow-utils && \
    groupadd -g 1000 lambda && \
    useradd -u 1000 -g lambda lambda && \
    chown lambda:lambda /function && \
    microdnf clean all

# Switch to lambda user for all subsequent operations
USER lambda

# Copy function code and requirements
COPY --chown=lambda:lambda main.py .
COPY --chown=lambda:lambda requirements.txt .
COPY --chown=lambda:lambda trading/ trading/

# Install packages to a temporary directory, clean them up, and copy to function directory
RUN pip install --target . --no-cache-dir -r requirements.txt && \
    # Remove all test/example/doc directories
    find . -type d -name "tests" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "test" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "*test*" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "examples" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "docs" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "doc" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "*docs*" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "documentation" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "locale" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "locales" -not -path "*/boto*/*" -exec rm -rf {} + && \
    # Remove development files
    find . -name "*.c" -not -path "*/boto*/*" -delete && \
    find . -name "*.h" -not -path "*/boto*/*" -delete && \
    find . -name "*.pxd" -not -path "*/boto*/*" -delete && \
    find . -name "*.pyx" -not -path "*/boto*/*" -delete && \
    find . -name "*.so.*" -not -path "*/boto*/*" -delete && \
    find . -name "*.pyi" -not -path "*/boto*/*" -delete && \
    find . -name "*.pyc" -not -path "*/boto*/*" -delete && \
    find . -name "*.pyo" -not -path "*/boto*/*" -delete && \
    find . -name "*.egg-info" -not -path "*/boto*/*" -exec rm -rf {} + && \
    # Remove documentation files
    find . -name "README*" -not -path "*/boto*/*" -delete && \
    find . -name "readme*" -not -path "*/boto*/*" -delete && \
    find . -name "CHANGELOG*" -not -path "*/boto*/*" -delete && \
    find . -name "AUTHORS*" -not -path "*/boto*/*" -delete && \
    find . -name "CONTRIBUTING*" -not -path "*/boto*/*" -delete && \
    find . -name "LICENSE*" -not -path "*/boto*/*" -delete && \
    find . -name "*.md" -not -path "*/boto*/*" -delete && \
    find . -name "*.rst" -not -path "*/boto*/*" -delete && \
    # Remove cache and build artifacts
    find . -name "__pycache__" -not -path "*/boto*/*" -exec rm -rf {} + && \
    # Remove data files
    find . -name "*.csv" -not -path "*/boto*/*" -delete && \
    find . -name "*.json" -not -path "*/boto*/*" -delete && \
    find . -name "*.yaml" -not -path "*/boto*/*" -delete && \
    find . -name "*.xml" -not -path "*/boto*/*" -delete && \
    find . -name "*.ipynb" -not -path "*/boto*/*" -delete && \
    find . -name "sample*" -not -path "*/boto*/*" -delete && \
    find . -name "example*" -not -path "*/boto*/*" -delete && \
    find . -name "dataset*" -not -path "*/boto*/*" -delete && \
    find . -name "*.pkl" -not -path "*/boto*/*" -delete

# Create deployment package
RUN zip -r /lambda_function.zip .

CMD ["main.lambda_handler"]