FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils gcc gcc-c++ make

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .

# Update pip and setuptools
RUN pip install --upgrade pip setuptools wheel

# Install packages and perform aggressive cleanup
RUN pip install --target . --no-cache-dir -r requirements.txt && \
# Perform cleanup while preserving necessary files
    find . -type d -name "tests" -not -path "*/boto*/*" -not -path "*/numpy/*" -exec rm -rf {} + && \
    find . -type d -name "test" -not -path "*/boto*/*" -not -path "*/numpy/*" -exec rm -rf {} + && \
    find . -type d -name "*test*" -not -path "*/boto*/*" -not -path "*/numpy/*" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "docs" -exec rm -rf {} + && \
    find . -type d -name "doc" -exec rm -rf {} + && \
    find . -type d -name "*docs*" -exec rm -rf {} + && \
    find . -type d -name "documentation" -exec rm -rf {} + && \
    find . -type d -name "locale" -exec rm -rf {} + && \
    # Remove unnecessary files while preserving critical ones
    find . -name "*.c" -not -path "*/numpy/core/*" -not -path "*/numpy/random/*" -delete && \
    find . -name "*.h" -not -path "*/numpy/core/*" -not -path "*/numpy/random/*" -delete && \
    find . -name "*.pxd" -not -path "*/numpy/core/*" -not -path "*/numpy/random/*" -delete && \
    find . -name "*.pyx" -not -path "*/numpy/core/*" -not -path "*/numpy/random/*" -delete && \
    find . -name "*.pyi" -delete && \
    find . -name "*.pyc" -delete && \
    find . -name "*.pyo" -delete && \
    find . -name "*.egg-info" -exec rm -rf {} + && \
    # Remove documentation files
    find . -name "README*" -delete && \
    find . -name "CHANGELOG*" -delete && \
    find . -name "AUTHORS*" -delete && \
    find . -name "CONTRIBUTING*" -delete && \
    find . -name "LICENSE*" -delete && \
    find . -name "*.md" -delete && \
    find . -name "*.rst" -delete && \
    # Remove cache
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
    find . -name "*.pkl" -delete && \
    # Remove specific large package components
    find . -type d -name "pandas/tests" -not -path "/boto/" -exec rm -rf {} + && \
    find . -type d -name "numpy/tests" -not -path "/boto/" -exec rm -rf {} + && \
    find . -type d -name "numpy/doc" -not -path "/boto/*" -exec rm -rf {} +

# Create deployment package
RUN zip -r /lambda2_function.zip .

CMD ["main.lambda_handler"]