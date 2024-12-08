FROM public.ecr.aws/lambda/python:3.12@sha256:92c88c1adc374b073b07b12bd4045497af7da68230d47c2b330423115c5850dc

# Install required tools
RUN microdnf install -y zip findutils

# Create function directory
WORKDIR /function

# Copy function code and requirements
COPY main.py .
COPY requirements.txt .
COPY trading/ trading/

# Install packages and clean up unnecessary files
RUN pip install --no-cache-dir -r requirements.txt && \
    find /var/lang/lib/python3.12/site-packages -type d -name "tests" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -type d -name "examples" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -type d -name "*.dist-info" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -type d -name "docs" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -type d -name "doc" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -type d -name "documentation" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -type d -name "test" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -name "README*" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "readme*" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "CHANGELOG*" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "AUTHORS*" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "CONTRIBUTING*" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "LICENSE*" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.md" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.rst" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.pyc" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.pyo" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "__pycache__" -exec rm -rf {} + && \
    find /var/lang/lib/python3.12/site-packages -name "*.csv" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.json" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.yaml" -delete && \
    find /var/lang/lib/python3.12/site-packages -name "*.xml" -delete

# Create deployment package
RUN zip -r /lambda_function.zip .

CMD ["main.lambda_handler"]