FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools and development files
RUN microdnf install -y zip findutils gcc make python3-devel

# Create the proper Python package directory structure
WORKDIR /opt/python/lib/python3.12/site-packages

# Create a requirements.txt file (each package on a new line)
RUN echo "numpy==1.26.0" > /tmp/requirements.txt && \
    echo "pandas==2.2.0" >> /tmp/requirements.txt && \
    echo "pyarrow==14.0.1" >> /tmp/requirements.txt && \
    echo "databento==0.45.0" >> /tmp/requirements.txt && \
    echo "databento-dbn==0.23.1" >> /tmp/requirements.txt

# Install all packages at once
RUN pip install --no-cache-dir -r /tmp/requirements.txt -t .

# Clean up unnecessary files
RUN find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    find . -type f -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} + && \
    find . -type f -name "*.so" ! -name "_lib.cpython-312-x86_64-linux-gnu.so" -delete

# Create zip from the /opt directory
WORKDIR /opt
RUN zip -r /layer.zip .