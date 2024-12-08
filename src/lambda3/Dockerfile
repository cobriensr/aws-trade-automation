FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils gcc make python3-devel

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .

# Install packages directly in the function directory
# Clean up unnecessary files
RUN pip install --no-cache-dir -r requirements.txt && \
    cd /var/lang/lib/python3.12/site-packages && \
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -exec rm -rf {} + && \
    find . -type d -name "docs" -exec rm -rf {} + && \
    find . -type d -name "doc" -exec rm -rf {} + && \
    find . -type d -name "documentation" -exec rm -rf {} + && \
    find . -type d -name "test" -exec rm -rf {} + && \
    find . -type f -name "test_*.py" -delete && \
    find . -type f -name "*_test.py" -delete && \
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
    find . -type d -name "samples" -exec rm -rf {} + && \
    find . -type d -name "demo" -exec rm -rf {} + && \
    find . -name "*.csv" -delete && \
    find . -name "*.json" -delete && \
    find . -name "*.yaml" -delete && \
    find . -name "*.xml" -delete && \
    find . -name "*.pyproj" -delete && \
    find . -name "*.sln" -delete && \
    find . -name "tox.ini" -delete && \
    find . -name "setup.cfg" -delete && \
    find . -name "conftest.py" -delete && \
    find . -name ".coveragerc" -delete && \
    find . -name ".gitignore" -delete && \
    find . -name ".gitattributes" -delete

# Copy installed packages to the function directory
RUN cp -r /var/lang/lib/python3.12/site-packages/* .

# Create deployment package
RUN zip -r /lambda3_function.zip .

