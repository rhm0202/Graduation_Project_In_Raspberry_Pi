#!/bin/bash
set -e

# 스크립트 위치 기준으로 프로젝트 루트 경로 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

echo "pigpiod 데몬 설치 시도"
sudo apt-get install -y pigpio || echo "pigpio apt 설치 실패 — pip으로 대체 설치됩니다"

echo "pigpiod 부팅 시 자동 시작 등록"
sudo systemctl enable pigpiod 2>/dev/null || true

echo "가상환경 생성 ($PROJECT_ROOT/venv)"
python3 -m venv --system-site-packages "$PROJECT_ROOT/venv"

echo "가상환경 활성화"
source "$PROJECT_ROOT/venv/bin/activate"

echo "pip 업데이트"
python -m pip install --upgrade pip

echo "Python 라이브러리 설치"
pip install -r "$SCRIPT_DIR/requirements.txt"

echo "설치 확인"
python -c "import cv2, numpy, websockets; print('패키지 확인 완료')"

echo "설치 완료"