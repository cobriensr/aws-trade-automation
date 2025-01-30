FROM public.ecr.aws/docker/library/python:3.12.8-alpine3.21

# Switch to root for system installations
USER root
WORKDIR /function

# Install required tools and ensure musl compatibility
RUN apk add --no-cache \
findutils \
    gcc \
    gcompat \
    libc6-compat \
    libstdc++ \
    linux-headers \
    musl-dev \
    python3-dev \
    zip \
    && chown 1000:1000 /function

# Switch to lambda user for all subsequent operations
USER 1000:1000

# Copy function code and requirements
COPY --chown=1000:1000 main.py .
COPY --chown=1000:1000 requirements.txt .
COPY --chown=1000:1000 trading/ trading/

# Install packages to a temporary directory, clean them up, and copy to function directory
RUN pip install --target . --no-cache-dir -r requirements.txt && \
    # Copy necessary musl libraries
    cp /lib/ld-musl-x86_64.so.1 . && \
    cp /lib/libc.musl-x86_64.so.1 . && \
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
RUN mkdir -p /tmp/lambda && \
    zip -r /tmp/lambda/lambda_function.zip .

CMD ["main.lambda_handler"]