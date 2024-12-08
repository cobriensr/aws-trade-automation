FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils gcc make python3-devel

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .

# Install packages directly in the function directory
RUN pip install -r requirements.txt

# Clean up unnecessary files
RUN cd /var/lang/lib/python3.12/site-packages && \
    find . -type d -name "tests" -exec rm -rf {} + && \
    find . -type d -name "examples" -exec rm -rf {} + && \
    find . -type d -name "*.dist-info" -exec rm -rf {} + && \
    find . -type f -name "*.pyc" -delete && \
    find . -type f -name "*.pyo" -delete && \
    find . -type d -name "__pycache__" -exec rm -rf {} +

# Copy installed packages to the function directory
RUN cp -r /var/lang/lib/python3.12/site-packages/* .

# Create deployment package
RUN zip -r /lambda3_function.zip .

