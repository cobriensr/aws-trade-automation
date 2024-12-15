FROM amazonlinux:2023 AS builder

# Install build tools and Python as root
USER root
RUN dnf install -y gcc gcc-c++ make python3.12 python3.12-pip python3.12-devel shadow-utils && \
    useradd -m -u 1001 builder && \
    mkdir /build && \
    chown builder:builder /build && \
    dnf clean all

# Switch to non-root user for building
USER builder
WORKDIR /build

# Copy requirements file with correct ownership
COPY --chown=builder:builder requirements.txt .

# Install Python packages as non-root user
RUN pip3.12 install --no-cache-dir -r requirements.txt -t python/

FROM public.ecr.aws/lambda/python:3.12

# Switch to root for system installations and setup
USER root
WORKDIR /var/task

# Install Lambda Insights agent and set up user in a single layer
RUN microdnf install -y shadow-utils && \
    groupadd -g 1000 lambda && \
    useradd -u 1000 -g lambda lambda && \
    chown lambda:lambda /var/task && \
    curl -O https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm && \
    rpm -U lambda-insights-extension.rpm && \
    rm -f lambda-insights-extension.rpm && \
    microdnf remove -y shadow-utils && \
    microdnf clean all

# Switch to lambda user
USER lambda

# Copy built packages and main.py with correct ownership
COPY --chown=lambda:lambda --from=builder /build/python /var/task
COPY --chown=lambda:lambda main.py /var/task/

CMD [ "main.lambda_handler" ]