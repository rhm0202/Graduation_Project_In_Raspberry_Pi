FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 시스템 패키지
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libc6-dev \
    libglib2.0-0 \
    libgl1 \
    libjpeg-dev \
    zlib1g-dev \
    ffmpeg \
    v4l-utils \
    libcamera-dev \
    python3-picamera2 \
    && rm -rf /var/lib/apt/lists/*

# pip 업데이트
RUN pip install --upgrade pip

# Python 패키지
RUN pip install --no-cache-dir \
    numpy \
    opencv-python \
    ultralytics \
    picamera2 \
    RPi.GPIO

# 코드 복사
COPY . /app

# 기본 실행 (쉘로)
CMD ["bash"]