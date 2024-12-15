FROM amazonlinux:2023 AS builder

# Install build tools and Python as root
USER root
RUN dnf install -y gcc gcc-c++ make python3.12 python3.12-pip python3.12-devel shadow-utils && \
    useradd -m -u 1001 builder && \
    mkdir /build && \
    chown 1001:1001 /build && \
    dnf clean all

# Switch to non-root user for building
USER 1001:1001
WORKDIR /build

# Copy requirements file with correct ownership
COPY --chown=1001:1001 requirements.txt .

# Install Python packages as non-root user
RUN pip3.12 install --no-cache-dir -r requirements.txt -t python/

FROM public.ecr.aws/docker/library/python:3.12.8

# Switch to root for system installations and setup
USER root
WORKDIR /var/task

# Add and install Lambda Insights agent
ADD https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm /tmp/
RUN rpm -U /tmp/lambda-insights-extension.rpm && \
    rm -f /tmp/lambda-insights-extension.rpm && \
    chown -R 1000:1000 /var/task

# Switch to lambda user
USER 1000:1000

# Copy built packages and main.py with correct ownership
COPY --chown=1000:1000 --from=builder /build/python /var/task
COPY --chown=1000:1000 main.py /var/task/

CMD [ "main.lambda_handler" ]