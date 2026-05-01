#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="$PROJECT_ROOT/venv"
SERVER="$PROJECT_ROOT/Server/rpi_server.py"

# 가상환경 확인
if [ ! -f "$VENV/bin/activate" ]; then
    echo "가상환경이 없습니다. setup/install.sh를 먼저 실행해주세요."
    exit 1
fi

echo "가상환경 활성화"
source "$VENV/bin/activate"

echo "pigpiod 데몬 확인"
if ! pgrep -x pigpiod > /dev/null; then
    echo "pigpiod 시작"
    sudo pigpiod
fi

echo "서버 실행"
python "$SERVER"
