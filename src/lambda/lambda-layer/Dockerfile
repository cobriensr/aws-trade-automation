FROM public.ecr.aws/lambda/python:3.12

# Install required tools and development files
RUN microdnf install -y zip findutils gcc make python3-devel

# Create the proper Python package directory structure
RUN mkdir -p /opt/python/lib/python3.12/site-packages

# Copy requirements and install packages
COPY requirements.txt .

# Install databento with all dependencies
RUN pip install --no-cache-dir databento -t /opt/python/lib/python3.12/site-packages/ && \
    pip install --no-cache-dir databento-dbn -t /opt/python/lib/python3.12/site-packages/

# Clean up unnecessary files
RUN cd /opt/python/lib/python3.12/site-packages/ && \
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    find . -type f -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} +

# Create zip from the /opt directory
WORKDIR /opt
RUN zip -r /layer.zip .