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

FROM public.ecr.aws/docker/library/python:3.12.8-alpine3.21

# Install required tools and ensure musl compatibility
RUN apk add --no-cache \
    rpm \
    gcc \
    python3-dev \
    musl-dev \
    linux-headers \
    zip \
    findutils \
    gcompat \
    libc6-compat \
    libstdc++ \
    curl \
    build-base \
    rust \
    cargo \
    cmake \
    make

# Install the Lambda Runtime Interface Client
RUN curl -Lo /usr/local/bin/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie && \
    chmod +x /usr/local/bin/aws-lambda-rie

# Switch to root for system installations and setup
USER root
WORKDIR /var/task

# Add and install Lambda Insights agent
ADD https://lambda-insights-extension.s3-ap-northeast-1.amazonaws.com/amazon_linux/lambda-insights-extension.rpm /tmp/
RUN rpm -U /tmp/lambda-insights-extension.rpm && \
    rm -f /tmp/lambda-insights-extension.rpm && \
    cp /lib/ld-musl-x86_64.so.1 . && \
    cp /lib/libc.musl-x86_64.so.1 . && \
    chown -R 1000:1000 /var/task

# Install AWS Lambda Runtime Interface Client
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir awslambdaric

# Switch to lambda user
USER 1000:1000

# Copy built packages and main.py with correct ownership
COPY --chown=1000:1000 --from=builder /build/python /var/task
COPY --chown=1000:1000 main.py /var/task/

# Create a lib directory and ensure necessary libraries are included
RUN mkdir -p lib && \
    cp /lib/ld-musl-x86_64.so.1 lib/ && \
    cp /lib/libc.musl-x86_64.so.1 lib/ && \
    # Add any other necessary shared libraries
    for lib in $(ldd $(which python3) | grep -v linux-vdso | cut -d ' ' -f 3); do \
        if [ -f "$lib" ]; then \
            cp "$lib" lib/ || true; \
        fi \
    done

# Use the Runtime Interface Client as the entrypoint
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "main.lambda_handler" ]