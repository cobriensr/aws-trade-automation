FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils gcc make python3-devel

# Set working directory to a temporary location
WORKDIR /tmp/build

# Install packages to a clean directory
RUN python -m venv /tmp/venv && \
    source /tmp/venv/bin/activate && \
    pip install --no-cache-dir \
        numpy==1.26.0 \
        pandas==2.2.0 \
        pyarrow==14.0.1 \
        databento==0.45.0 \
        databento-dbn==0.23.1

# Create the Lambda layer structure
RUN mkdir -p /opt/python && \
    cp -r /tmp/venv/lib/python3.12/site-packages/* /opt/python/

# Clean up unnecessary files
RUN cd /opt/python && \
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    find . -type f -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} + && \
    find . -type f -name "*.so" ! -name "_lib.cpython-312-x86_64-linux-gnu.so" -delete

# Create the final layer zip
WORKDIR /
RUN cd /opt && zip -r /layer.zip .