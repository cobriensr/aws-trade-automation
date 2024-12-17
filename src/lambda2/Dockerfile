FROM amazonlinux:2023 AS builder

# Install build tools and Python
RUN dnf install -y gcc gcc-c++ make python3.12 python3.12-pip python3.12-devel && \
dnf clean all

# Create and set working directory
WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install Python packages
RUN pip3.12 install --no-cache-dir -r requirements.txt -t python/

FROM public.ecr.aws/lambda/python:3.12

# Install Lambda Insights agent
RUN curl -O https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm && \
    rpm -U lambda-insights-extension.rpm && \
    rm -f lambda-insights-extension.rpm

# Copy built packages from builder stage
COPY --from=builder /build/python /var/task
COPY main.py /var/task/

