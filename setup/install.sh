#!/bin/bash
set -e

echo "패키지 목록 업데이트"
sudo apt-get update

echo "시스템 패키지 설치"
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-picamera2 \
    ffmpeg \
    v4l-utils \
    libgl1 \
    libglib2.0-0

echo "가상환경 생성"
python3 -m venv --system-site-packages venv

echo "가상환경 활성화"
source venv/bin/activate

echo "pip 업데이트"
python -m pip install --upgrade pip

echo "Python 라이브러리 설치"
pip install -r requirements.txt

echo "설치 확인"
python -c "import cv2, numpy, websockets; print('패키지 확인 완료')"

echo "설치 완료"