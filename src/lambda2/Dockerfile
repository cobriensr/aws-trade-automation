FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils gcc make python3-devel

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .

# Install packages directly in the function directory
RUN pip install --no-cache-dir -r requirements.txt

# Clean up unnecessary files
RUN cd /var/lang/lib/python3.12/site-packages && \
    -type d -name "tests" -exec rm -rf {} + && \
    -type d -name "examples" -exec rm -rf {} + && \
    -type d -name "*.dist-info" -exec rm -rf {} + && \
    -type d -name "docs" -exec rm -rf {} + && \
    -type d -name "doc" -exec rm -rf {} + && \
    -type d -name "documentation" -exec rm -rf {} + && \
    -type d -name "test" -exec rm -rf {} + && \
    -type f -name "test_*.py" -delete && \
    -type f -name "*_test.py" -delete && \
    -name "README*" -delete && \
    -name "readme*" -delete && \
    -name "CHANGELOG*" -delete && \
    -name "AUTHORS*" -delete && \
    -name "CONTRIBUTING*" -delete && \
    -name "LICENSE*" -delete && \
    -name "*.md" -delete && \
    -name "*.rst" -delete && \
    -name "*.pyc" -delete && \
    -name "*.pyo" -delete && \
    -name "__pycache__" -exec rm -rf {} + && \
    -type d -name "samples" -exec rm -rf {} + && \
    -type d -name "demo" -exec rm -rf {} + && \
    -name "*.csv" -delete && \
    -name "*.json" -delete && \
    -name "*.yaml" -delete && \
    -name "*.xml" -delete && \
    -name "*.pyproj" -delete && \
    -name "*.sln" -delete && \
    -name "tox.ini" -delete && \
    -name "setup.cfg" -delete && \
    -name "conftest.py" -delete && \
    -name ".coveragerc" -delete && \
    -name ".gitignore" -delete && \
    -name ".gitattributes" -delete

# Copy installed packages to the function directory
RUN cp -r /var/lang/lib/python3.12/site-packages/* .

# Create deployment package
RUN zip -r /lambda2_function.zip .