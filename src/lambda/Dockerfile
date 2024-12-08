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
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -exec rm -rf {} + && \
    find . -type d -name "docs" -exec rm -rf {} + && \
    find . -type d -name "doc" -exec rm -rf {} + && \
    find . -type d -name "documentation" -exec rm -rf {} + && \
    find . -type d -name "test" -exec rm -rf {} + && \
    find . -name "README*" -delete && \
    find . -name "readme*" -delete && \
    find . -name "CHANGELOG*" -delete && \
    find . -name "AUTHORS*" -delete && \
    find . -name "CONTRIBUTING*" -delete && \
    find . -name "LICENSE*" -delete && \
    find . -name "*.md" -delete && \
    find . -name "*.rst" -delete && \
    find . -name "*.pyc" -delete && \
    find . -name "*.pyo" -delete && \
    find . -name "__pycache__" -exec rm -rf {} + && \
    find . -name "*.csv" -delete && \
    find . -name "*.json" -delete && \
    find . -name "*.yaml" -delete && \
    find . -name "*.xml" -delete

# Create deployment package
RUN zip -r /lambda_function.zip .

CMD ["main.lambda_handler"]