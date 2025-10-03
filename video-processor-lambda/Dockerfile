# --- DEFINITIVE FINAL DOCKERFILE ---
FROM public.ecr.aws/lambda/python:3.10-x86_64
WORKDIR /var/task

# 1. Install necessary system dependencies (Keep system libraries like FFmpeg dependencies)
# Note: Removed fontconfig/dejavu-sans-fonts as we are bundling the font now.
RUN yum update -y && \
    yum install -y \
        gcc \
        gcc-c++ \
        python3-devel \
        make \
        unzip \
        tar \
    && yum clean all

# 2. Install ALL Python Dependencies into /var/task
COPY requirements.txt .
RUN pip install -r requirements.txt awslambdaric -t /var/task

# 3. Copy the Lambda handler code, fonts, and binaries
COPY lambda_function.py .
COPY images /var/task/images 
# --- NEW: Copy the bundled font directory ---
COPY fonts /var/task/fonts
RUN chmod -R 755 /var/task/fonts

# --- NEW LINE: Copy the fade transition video ---
COPY fade_transition.mp4 /var/task/fade_transition.mp4 

# 4. Binary Setup (FFmpeg and ImageMagick)
COPY ffmpeg .
RUN chmod +x ./ffmpeg

CMD [ "lambda_function.lambda_handler" ]