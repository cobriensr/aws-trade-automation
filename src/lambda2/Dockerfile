FROM public.ecr.aws/lambda/python:3.12 AS builder

# Install build tools
RUN yum install -y gcc gcc-c++ make cmake

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -t /var/task/

FROM public.ecr.aws/lambda/python:3.12

# Copy the built dependencies
COPY --from=builder /var/task /var/task

# Copy your function code
COPY main.py /var/task/

# Set the CMD to your handler
CMD [ "main.lambda_handler" ]