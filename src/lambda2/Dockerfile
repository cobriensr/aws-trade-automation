FROM public.ecr.aws/amazonlinux/amazonlinux:2023 AS builder

# Set environment variables for build stage
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install build tools and Python
RUN dnf install -y \
    gcc \
    gcc-c++ \
    make \
    python3.12 \
    python3.12-pip \
    python3.12-devel \
    && dnf clean all \
    && rm -rf /var/cache/dnf/* \
    && rm -rf /var/tmp/* \
    && rm -rf /tmp/*

# Create and set working directory
WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install Python packages with specific options
RUN python3.12 -m pip install --upgrade pip && \
    # First install without dependencies to handle complex dependency trees
    python3.12 -m pip install --no-cache-dir --no-deps -r requirements.txt -t python/ && \
    # Then install with dependencies
    python3.12 -m pip install --no-cache-dir -r requirements.txt

FROM public.ecr.aws/lambda/python:3.12

# Set runtime environment variables
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONIOENCODING=UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Lambda Insights agent
RUN curl -O https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm && \
    rpm -U lambda-insights-extension.rpm && \
    rm -f lambda-insights-extension.rpm

# Create and prepare task directory
WORKDIR /var/task

# Copy built packages from builder stage and application code
COPY --from=builder /build/python/ ./
COPY main.py .

# Set permissions
RUN chmod 755 main.py && \
    chmod -R 755 .

# Specify the handler function
CMD ["main.lambda_handler"]