FROM python:3.11-bookworm

ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    pkg-config \
    git \
    wget \
    curl \
    ffmpeg \
    v4l-utils \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libjpeg-dev \
    zlib1g-dev \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    gfortran \
    libcamera-dev \
    libcap-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "main.py"]