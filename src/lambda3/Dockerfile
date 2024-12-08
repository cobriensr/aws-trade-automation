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
RUN pip install python-dotenv

# Create deployment package
RUN zip -r /lambda3_function.zip .

# List contents to verify structure
RUN unzip -l /lambda3_function.zip