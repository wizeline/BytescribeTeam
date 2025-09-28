# --- DEFINITIVE FINAL DOCKERFILE ---
FROM public.ecr.aws/lambda/python:3.10-x86_64
WORKDIR /var/task

# 1. Install necessary system dependencies (GCC, Python Dev)
RUN yum update -y && \
    yum install -y \
        gcc \
        gcc-c++ \
        python3-devel \
        make \
        unzip \
        tar && \
    yum clean all

# 2. Install ALL Python Dependencies into /var/task
COPY requirements.txt .
RUN pip install -r requirements.txt awslambdaric -t /var/task

# 3. Copy the Lambda handler code and the FFmpeg binary
COPY lambda_function.py .
COPY ffmpeg .
RUN chmod +x ./ffmpeg

CMD [ "lambda_function.lambda_handler" ]