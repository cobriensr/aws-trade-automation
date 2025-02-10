FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS builder

# Set environment variables for build stage
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PROGRESS_MSG=1

# Install development tools and Python packages in a single layer to keep the image size smaller
RUN dnf groupinstall -y "Development Tools" && \
    dnf install -y \
        python3.12 \
        python3.12-pip \
        python3.12-devel \
        procps \
        kernel-headers \
        systemd-devel && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Create and set working directory
WORKDIR /build

# Copy and install requirements
COPY requirements.txt .

# Install packages
RUN echo "Upgrading pip..." && \
    python3.12 -m pip install --upgrade pip && \
    echo "Installing Python packages..." && \
    python3.12 -m pip install --no-cache-dir \
        --target python/ \
        -r requirements.txt

FROM public.ecr.aws/lambda/python:3.12

# Set runtime environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Lambda Insights agent
RUN echo "Installing Lambda Insights agent..." && \
    curl -O https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm && \
    rpm -U lambda-insights-extension.rpm && \
    rm -f lambda-insights-extension.rpm && \
    echo "Lambda Insights agent installed successfully"

# Create and prepare task directory
WORKDIR /var/task

# Copy built packages from builder stage and application code
COPY --from=builder /build/python/ ./
COPY main.py .

# Set permissions
RUN echo "Setting file permissions..." && \
    chmod 755 main.py && \
    chmod -R 755 . && \
    echo "File permissions set successfully" && \
    echo "Build completed successfully"

# Set image metadata
LABEL maintainer="AWS Lambda Container" \
version="1.0" \
description="Lambda Container for trading-prod-symbol-lookup"

# Specify the handler function
CMD ["main.lambda_handler"]