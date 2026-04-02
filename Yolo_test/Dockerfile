FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# 필수 시스템 라이브러리 (최소 구성)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libgl1 \
    libjpeg-dev \
    zlib1g-dev \
    ffmpeg \
    v4l-utils \
    && rm -rf /var/lib/apt/lists/*

# pip 최신화
RUN pip install --upgrade pip

# Python 패키지 설치 (최소)
RUN pip install \
    numpy \
    opencv-python \
    ultralytics \
    RPi.GPIO

# 코드 복사
COPY . /app

# 실행
CMD ["python", "yolo_test.py"]