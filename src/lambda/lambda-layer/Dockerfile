FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils gcc make python3-devel

# Create Lambda layer directory structure
RUN mkdir -p /opt/python/lib/python3.12/site-packages

# Install packages directly to the Lambda layer directory
RUN pip install --no-cache-dir --target /opt/python/lib/python3.12/site-packages \
    numpy==1.26.0 \
    pandas==2.2.0 \
    pyarrow==14.0.1 \
    databento==0.45.0 \
    databento-dbn==0.23.1

# Clean up unnecessary files
RUN cd /opt/python/lib/python3.12/site-packages && \
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    find . -type f -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} +

# Create zip
WORKDIR /opt
RUN zip -r /layer.zip .

# List contents to verify structure
RUN unzip -l /layer.zip