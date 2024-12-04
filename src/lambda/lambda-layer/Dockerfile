FROM public.ecr.aws/lambda/python:3.12

# Install required tools
RUN microdnf install -y zip findutils

# Create a working directory
WORKDIR /package

# Copy requirements and install packages
COPY requirements.txt .

# Install only necessary packages and clean up
RUN pip install --no-cache-dir --no-deps databento && \
    pip install --no-cache-dir -r requirements.txt -t . && \
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    find . -type f -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} +

# List contents and sizes
RUN ls -la
RUN du -h -d 1 .

# Create zip
RUN zip -r layer.zip .

# Move to a location we can copy from
RUN mv layer.zip /