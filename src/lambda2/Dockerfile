FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .

# Install packages and perform aggressive cleanup
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
    find . -name "*.pkl" -not -path "*/boto*/*" -delete && \
    # Remove specific large package components
    find . -type d -name "pandas/tests" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "numpy/tests" -not -path "*/boto*/*" -exec rm -rf {} + && \
    find . -type d -name "numpy/doc" -not -path "*/boto*/*" -exec rm -rf {} +

# Create deployment package
RUN zip -r /lambda2_function.zip .

CMD ["main.lambda_handler"]