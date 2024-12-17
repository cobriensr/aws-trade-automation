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

# Install required tools and Runtime Interface Emulator
RUN apk add --no-cache \
    gcompat \
    libc6-compat \
    libstdc++ \
    curl && \
    curl -Lo /usr/local/bin/aws-lambda-rie https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie && \
    chmod +x /usr/local/bin/aws-lambda-rie && \
    pip install --no-cache-dir awslambdaric

WORKDIR /var/task

# Copy built packages and main.py with correct ownership
COPY --chown=1000:1000 --from=builder /build/python /var/task
COPY --chown=1000:1000 main.py /var/task/

# Create lib directory for compatibility
RUN mkdir -p lib && \
    cp /lib/ld-musl-x86_64.so.1 lib/ && \
    cp /lib/libc.musl-x86_64.so.1 lib/

# Use Python with Lambda RIE as entrypoint
ENTRYPOINT [ "/usr/local/bin/python", "-m", "awslambdaric" ]
CMD [ "main.lambda_handler" ]